"""GPU detection via nvidia-smi subprocess.

Works without any extra Python packages. nvidia-smi ships with the
NVIDIA driver and is available on AWS EC2 G4dn instances.
"""

import subprocess
import os

from core.logging_config import get_logger

logger = get_logger(__name__)


class GPUInfo(object):
    """Holds information about a single GPU."""

    def __init__(self, index, name, vram_total_mb, vram_free_mb, util_pct):
        self.index = index
        self.name = name
        self.vram_total_mb = vram_total_mb
        self.vram_free_mb = vram_free_mb
        self.util_pct = util_pct

    def __repr__(self):
        return 'GPUInfo(index=%d, name=%r, vram=%dMB)' % (
            self.index, self.name, self.vram_total_mb)

    def to_dict(self):
        return {
            'index': self.index,
            'name': self.name,
            'vram_total_mb': self.vram_total_mb,
            'vram_free_mb': self.vram_free_mb,
            'util_pct': self.util_pct,
        }


def detect_gpus():
    """Detect NVIDIA GPUs via nvidia-smi.

    Returns:
        list[GPUInfo]: Detected GPUs. Empty list if nvidia-smi unavailable.
    """
    try:
        # CREATE_NO_WINDOW prevents a console window flashing on Windows
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = 0x08000000  # subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            [
                'nvidia-smi',
                '--query-gpu=index,name,memory.total,memory.free,utilization.gpu',
                '--format=csv,noheader,nounits',
            ],
            capture_output=True,
            text=True,
            timeout=10,
            **kwargs
        )
        if result.returncode != 0:
            logger.warning("nvidia-smi returned non-zero: %s", result.stderr)
            return []

        gpus = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 5:
                continue
            try:
                gpus.append(GPUInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    vram_total_mb=int(parts[2]),
                    vram_free_mb=int(parts[3]),
                    util_pct=int(parts[4]),
                ))
            except (ValueError, IndexError) as exc:
                logger.warning("Failed to parse GPU line %r: %s", line, exc)

        logger.info("Detected %d GPU(s): %s", len(gpus), [g.name for g in gpus])
        return gpus

    except FileNotFoundError:
        logger.info("nvidia-smi not found -- no NVIDIA GPUs detected")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out")
        return []
    except Exception as exc:
        logger.warning("GPU detection failed: %s", exc)
        return []


def get_available_gpus(reserved=1, config=None):
    """Return GPUs available for rendering after reserving some for interactive use.

    Args:
        reserved (int): Number of GPUs to reserve (not used for rendering).
                        Overridden by config.get_reserved_gpus() if config provided.
        config: Optional ProjectConfig instance.

    Returns:
        list[GPUInfo]: GPUs available for render (may be empty).
    """
    if config is not None:
        try:
            reserved = config.get_reserved_gpus()
        except Exception:
            pass

    all_gpus = detect_gpus()
    available = all_gpus[reserved:] if reserved < len(all_gpus) else []

    logger.info(
        "GPUs: total=%d reserved=%d available=%d",
        len(all_gpus), reserved, len(available)
    )
    return available
