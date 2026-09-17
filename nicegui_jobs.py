"""CPU work for the NiceGUI POC, isolated from the existing applications."""

import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from functools import partial

_pool = None


async def cpu_job(function, *args, **kwargs):
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'))
    return await asyncio.get_running_loop().run_in_executor(_pool, partial(function, *args, **kwargs))


def shutdown_jobs():
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None
