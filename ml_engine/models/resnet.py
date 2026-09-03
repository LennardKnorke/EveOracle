# ml_engine/models/resnet.py

import torch
import torch.nn as nn


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.15):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
        )
        self.act = nn.SiLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.block(x))


class TabularResNet(nn.Module):
    """
    Deep Tabular Residual Network for 1v1 matchup regression.
    Accepts concatenated P1 (Focal) and P2 (Opponent) feature vectors.
    """
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        num_blocks: int = 3,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_blocks = num_blocks

        # Initial feature projection
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
        )

        # Residual backbone
        self.res_blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout=dropout) for _ in range(num_blocks)
        ])

        # Output regression head (predicts signed log10 ISK trade)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.SiLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.input_layer(x)
        for block in self.res_blocks:
            h = block(h)
        return self.head(h)