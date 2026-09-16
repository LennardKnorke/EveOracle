# ml_engine/models/siamese.py

import torch
import torch.nn as nn


class PilotShipEncoder(nn.Module):
    """
    Shared sub-network that maps a single combatant's stats + ship dogma to an embedding vector.
    """
    def __init__(self, single_pilot_dim: int, embed_dim: int = 128, dropout: float = 0.15):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(single_pilot_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class SiameseCombatNet(nn.Module):
    """
    Dual-branch weight-shared Siamese network with joint physics support.
    Maps P1 and P2 through the identical encoder, then concatenates with relative combat physics.
    """
    def __init__(
        self,
        input_dim: int,
        single_dim: int,
        phys_dim: int = 7,
        embed_dim: int = 128,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.single_dim = single_dim
        self.phys_dim = phys_dim
        self.embed_dim = embed_dim

        # Shared encoder for both combatants
        self.encoder = PilotShipEncoder(single_dim, embed_dim=embed_dim, dropout=dropout)

        # Comparative Interaction Head [z1, z2, z1 - z2, z1 * z2, phys]
        interaction_dim = (embed_dim * 4) + phys_dim
        self.head = nn.Sequential(
            nn.Linear(interaction_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.SiLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(embed_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        p1 = x[:, :self.single_dim]
        p2 = x[:, self.single_dim : self.single_dim * 2]

        z1 = self.encoder(p1)
        z2 = self.encoder(p2)

        diff = z1 - z2
        mult = z1 * z2

        if self.phys_dim > 0:
            phys = x[:, self.single_dim * 2 :]
            interaction = torch.cat([z1, z2, diff, mult, phys], dim=1)
        else:
            interaction = torch.cat([z1, z2, diff, mult], dim=1)

        return self.head(interaction)