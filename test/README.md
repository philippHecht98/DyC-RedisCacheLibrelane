# Pytest + Cocotb Basics

Minimal test file example:

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb_tools.runner import get_runner


class BasicTester:
    def __init__(self, dut):
        self.dut = dut
        self.clk = dut.clk


@cocotb.test()
async def test_smoke(dut):
	tester = BasicTester(dut)
	clock = Clock(tester.clk, 10, unit="ns")
	cocotb.start_soon(clock.start())
	await RisingEdge(tester.clk)


def test_pipeline_runner():
	runner = get_runner("icarus")
	runner.build(sources=["src/redis_cache_top.v"], hdl_toplevel="redis_cache_top")
	runner.test(hdl_toplevel="redis_cache_top", test_module="basic_test")


if __name__ == "__main__":
	test_pipeline_runner()
```

What to look out for:

- File name matches `test_*.py` or `*_test.py`.
- Pytest entrypoint function name starts with `test_`.
- Cocotb tests use `@cocotb.test()` inside the same module or a discoverable module.
- `test_module` matches the Python module name (file name without `.py`).
- Keep the `__main__` block if you want to run the file directly.

Run all tests from the repository root:

```
pytest
```
