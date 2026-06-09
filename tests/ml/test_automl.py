import sys
import os
import pytest
from unittest import mock

from ml.automl_cli import create_parser, format_evidence_chain, evaluate_promotion

def test_argument_parsing():
    parser = create_parser()
    
    # Test with default arguments
    args = parser.parse_args([])
    assert args.round == 1
    assert args.sf_games == 1000
    assert args.sf_visits == 50
    assert args.tr_lr == 0.002
    assert args.pk_games == 20
    assert args.pk_threshold == 0.55

    # Test with custom arguments
    custom_args = [
        "--round", "5",
        "--model-name", "custom_model",
        "--gpu", "1",
        "--sf-games", "500",
        "--sf-visits", "100",
        "--sf-threads", "8",
        "--sh-threads", "6",
        "--sh-samples", "150000",
        "--tr-kind", "b20c256",
        "--tr-batch", "256",
        "--tr-lr", "0.001",
        "--pk-games", "40",
        "--pk-visits-b", "256",
        "--pk-visits-w", "128",
        "--pk-threshold", "0.60"
    ]
    args = parser.parse_args(custom_args)
    assert args.round == 5
    assert args.model_name == "custom_model"
    assert args.gpu == 1
    assert args.sf_games == 500
    assert args.sf_visits == 100
    assert args.sf_threads == 8
    assert args.sh_threads == 6
    assert args.sh_samples == 150000
    assert args.tr_kind == "b20c256"
    assert args.tr_batch == 256
    assert args.tr_lr == 0.001
    assert args.pk_games == 40
    assert args.pk_visits_b == 256
    assert args.pk_visits_w == 128
    assert args.pk_threshold == 0.60

def test_evidence_chain_formatting():
    parser = create_parser()
    args = parser.parse_args([
        "--round", "2",
        "--sf-games", "800",
        "--tr-lr", "0.005",
        "--pk-threshold", "0.58"
    ])
    chain = format_evidence_chain(args)
    
    assert "PARAM EVIDENCE CHAIN" in chain
    assert "--round" in chain
    assert "2" in chain
    assert "--sf-games" in chain
    assert "800" in chain
    assert "--tr-lr" in chain
    assert "0.005" in chain
    assert "--pk-threshold" in chain
    assert "0.58" in chain

def test_promotion_evaluation():
    # Winrate equal to threshold
    assert evaluate_promotion(0.55, 0.55) is True
    # Winrate above threshold
    assert evaluate_promotion(0.60, 0.55) is True
    # Winrate below threshold
    assert evaluate_promotion(0.50, 0.55) is False
    # Winrate significantly below threshold
    assert evaluate_promotion(0.10, 0.55) is False

def test_log_redirection(tmp_path):
    from automl_cli import run_subprocess_redirected
    log_file = tmp_path / "test_redirect.log"
    cmd = [sys.executable, "-c", "import sys; print('hello redirection world'); sys.exit(0)"]
    success = run_subprocess_redirected(cmd, log_file)
    
    assert success is True
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "hello redirection world" in content

    # Test append mode
    cmd_append = [sys.executable, "-c", "import sys; print('second line appended'); sys.exit(0)"]
    success_append = run_subprocess_redirected(cmd_append, log_file, mode="a")
    assert success_append is True
    
    content_append = log_file.read_text(encoding="utf-8")
    assert "hello redirection world" in content_append
    assert "second line appended" in content_append


