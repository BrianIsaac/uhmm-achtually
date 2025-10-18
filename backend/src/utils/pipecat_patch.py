"""Monkey patch for Pipecat 0.0.90 race condition bug.

This fixes the AttributeError: '__process_queue' not found issue in FrameProcessor.
See: https://github.com/pipecat-ai/pipecat/issues/2385

The bug: __process_queue is created in __create_process_task() which is only called
after StartFrame is received. But __input_frame_task_handler() can receive frames
before StartFrame arrives, causing it to access the non-existent __process_queue.

Solution: Initialize __process_queue earlier in __create_input_task() to ensure
it exists before any frames are processed.
"""

import asyncio
from pipecat.processors.frame_processor import FrameProcessor


# Save the original method
_original_create_input_task = FrameProcessor._FrameProcessor__create_input_task


def _patched_create_input_task(self):
    """Patched version that ensures __process_queue exists before processing frames."""
    # Call the original method
    _original_create_input_task(self)

    # Initialize __process_queue early to prevent race condition
    # This is normally created in __create_process_task() but we need it earlier
    if not hasattr(self, '_FrameProcessor__process_queue'):
        self._FrameProcessor__process_queue = asyncio.Queue()
        self._FrameProcessor__should_block_frames = False
        self._FrameProcessor__process_event = asyncio.Event()


def apply_pipecat_patch():
    """Apply the monkey patch to fix Pipecat 0.0.90 race condition."""
    FrameProcessor._FrameProcessor__create_input_task = _patched_create_input_task
    print("✓ Applied Pipecat 0.0.90 race condition patch")
