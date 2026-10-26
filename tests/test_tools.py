"""Unit tests for tool registration, execution, and vocal fillers."""

import pytest
from src.tools.registry import register_tool, get_all_tool_schemas, TOOL_REGISTRY
from src.tools.fillers import get_vocal_filler
from src.tools.runner import ToolRunner
from src.tools.builtin import get_current_time, get_weather, calculate, get_system_status


@pytest.mark.asyncio
async def test_builtin_tools():
    # 1. Test get_current_time
    time_res = await get_current_time()
    assert "time" in time_res
    assert "date" in time_res

    # 2. Test get_weather
    weather_res = await get_weather(city="London")
    assert weather_res["city"] == "London"
    assert "temperature_c" in weather_res
    assert "condition" in weather_res

    # 3. Test calculate
    calc_res = await calculate(expression="25 * 4 + 10")
    assert calc_res["result"] == 110
    assert calc_res["status"] == "success"

    # 4. Test get_system_status
    sys_res = await get_system_status()
    assert "cpu_percent" in sys_res
    assert "vad_status" in sys_res


@pytest.mark.asyncio
async def test_tool_runner():
    events = []
    runner = ToolRunner(on_event=lambda ev: events.append(ev))

    result, filler = await runner.execute_tool("get_weather", {"city": "Tokyo"})

    assert result["city"] == "Tokyo"
    assert filler is not None
    assert len(events) == 2
    assert events[0]["status"] == "executing"
    assert events[1]["status"] == "completed"


def test_tool_schemas_and_fillers():
    schemas = get_all_tool_schemas()
    assert len(schemas) >= 4

    # Verify weather filler
    weather_filler = get_vocal_filler("get_weather")
    assert isinstance(weather_filler, str)
    assert len(weather_filler) > 0
