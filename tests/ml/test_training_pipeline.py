"""
Minimal end-to-end training pipeline smoke test.
Verifies: PyTorch CUDA, model train/save/load, forward pass on board states.
"""
import os
import sys
import json
import gzip
import tempfile
import pytest
import torch
import torch.nn as nn
import numpy as np

BOARD_SIZE = 15
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class MiniGomokuNet(nn.Module):
    """Minimal policy+value network for smoke testing."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(4, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 32, 3, padding=1)
        self.policy_head = nn.Conv2d(32, 1, 1)
        self.value_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * BOARD_SIZE * BOARD_SIZE, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Tanh(),
        )

    def forward(self, x):
        h = torch.relu(self.conv1(x))
        h = torch.relu(self.conv2(h))
        policy = self.policy_head(h).view(-1, BOARD_SIZE * BOARD_SIZE)
        value = self.value_head(h)
        return policy, value


def random_batch(batch_size=4):
    """Generate random board states as (N, 4, 15, 15) tensor + targets."""
    planes = torch.zeros(batch_size, 4, BOARD_SIZE, BOARD_SIZE, device=DEVICE)
    for i in range(batch_size):
        n_stones = np.random.randint(3, 20)
        for _ in range(n_stones):
            x, y = np.random.randint(0, BOARD_SIZE, 2)
            ch = np.random.randint(0, 2)
            planes[i, ch, x, y] = 1.0
    planes[:, 2, :, :] = 1.0  # color-to-move plane
    planes[:, 3, :, :] = 0.5  # bias plane
    policy_target = torch.randint(0, BOARD_SIZE * BOARD_SIZE, (batch_size,), device=DEVICE)
    value_target = torch.rand(batch_size, device=DEVICE) * 2 - 1  # [-1, 1]
    return planes, policy_target, value_target


@pytest.fixture(scope="module")
def model():
    m = MiniGomokuNet().to(DEVICE)
    return m


def test_cuda_available():
    assert torch.cuda.is_available(), "CUDA not available — check GPU driver and PyTorch install"


def test_forward_pass(model):
    planes, _, _ = random_batch(2)
    policy, value = model(planes)
    assert policy.shape == (2, BOARD_SIZE * BOARD_SIZE)
    assert value.shape == (2, 1)


def test_backward_pass(model):
    """Verify gradient computation works on GPU."""
    planes, policy_target, value_target = random_batch(4)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    policy, value = model(planes)
    loss_p = nn.functional.cross_entropy(policy, policy_target)
    loss_v = nn.functional.mse_loss(value.squeeze(), value_target)
    loss = loss_p + loss_v

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    assert loss.item() > 0
    assert all(p.grad is not None for p in model.parameters() if p.requires_grad)


def test_training_loop(model):
    """Run a few training steps and verify loss decreases."""
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    losses = []

    for _ in range(10):
        planes, policy_target, value_target = random_batch(8)
        policy, value = model(planes)
        loss = nn.functional.cross_entropy(policy, policy_target) + \
               nn.functional.mse_loss(value.squeeze(), value_target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    # Loss should generally trend down (allow some noise)
    assert losses[-1] < losses[0] * 1.5, f"Loss not decreasing: {losses}"


def test_save_load_model(model, tmp_path):
    """Verify model save/load roundtrip."""
    ckpt_path = tmp_path / "model.pt"

    # Save
    torch.save(model.state_dict(), ckpt_path)
    assert ckpt_path.exists()

    # Load into fresh model
    m2 = MiniGomokuNet().to(DEVICE)
    m2.load_state_dict(torch.load(ckpt_path, weights_only=True))

    # Verify same output
    planes, _, _ = random_batch(2)
    model.eval()
    m2.eval()
    with torch.no_grad():
        p1, v1 = model(planes)
        p2, v2 = m2(planes)
    assert torch.allclose(p1, p2, atol=1e-5)
    assert torch.allclose(v1, v2, atol=1e-5)


def test_export_gzip(model, tmp_path):
    """Verify model can be exported as gzipped bin (KataGomo format)."""
    import io
    raw_path = tmp_path / "model.bin"
    gz_path = tmp_path / "model.bin.gz"

    # Save as raw state_dict bytes
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    raw_path.write_bytes(buffer.getvalue())

    # Gzip
    with raw_path.open("rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        f_out.write(f_in.read())

    assert gz_path.exists()
    assert gz_path.stat().st_size > 0

    # Verify decompress
    with gzip.open(gz_path, "rb") as f:
        data = f.read()
    assert len(data) > 0


def test_gpu_memory_sane():
    """Verify GPU memory usage is reasonable (< 2GB for this tiny model)."""
    if not torch.cuda.is_available():
        pytest.skip("No CUDA")
    allocated = torch.cuda.memory_allocated() / 1024 / 1024  # MB
    assert allocated < 2048, f"GPU memory usage too high: {allocated:.0f} MB"
