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
    Dual-branch weight-shared Siamese network.
    Enforces combat anti-symmetry: if P1 == P2, output is strictly 0.
    """
    def __init__(
        self,
        input_dim: int,
        embed_dim: int = 128,
        dropout: float = 0.15,
    ):
        super().__init__()
        assert input_dim % 2 == 0, f"Input dimension ({input_dim}) must be evenly divisible by 2 for Siamese network."
        self.single_dim = input_dim // 2
        self.embed_dim = embed_dim

        # Shared weight encoder for both combatants
        self.encoder = PilotShipEncoder(self.single_dim, embed_dim=embed_dim, dropout=dropout)

        # Comparative Interaction Head [z1, z2, z1 - z2, z1 * z2]
        interaction_dim = embed_dim * 4
        self.head = nn.Sequential(
            nn.Linear(interaction_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.SiLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(embed_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        p1 = x[:, :self.single_dim]
        p2 = x[:, self.single_dim:]

        z1 = self.encoder(p1)
        z2 = self.encoder(p2)

        diff = z1 - z2
        mult = z1 * z2
        interaction = torch.cat([z1, z2, diff, mult], dim=1)

        return self.head(interaction)