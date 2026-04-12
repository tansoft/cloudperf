---
name: cloudperf
description: "CloudPerf network performance testing tool. Query cloud network quality data including citysets, countries, cities, ASNs, and performance metrics between source and destination nodes. Use when the user asks about network performance, latency, cloud region comparison, or CloudPerf data."
license: MIT
allowed-tools: "Bash(python:*) Bash(fping:*) WebFetch"
dependency:
  python:
    - requests
  fping:
---

# CloudPerf Network Performance Query

## Overview

This skill provides direct REST API access to CloudPerf for querying network performance data. It replaces the need for a separate Lambda MCP deployment.

## Prerequisites

A config file at `~/.cloudperf/config.json` with:
```json
{
  "api_base": "https://your-cloudperf-api-endpoint",
  "username": "your_username",
  "password": "your_password"
}
```

Or set environment variables:
- `CLOUDPERF_API_BASE` - API base URL
- `CLOUDPERF_USERNAME`
- `CLOUDPERF_PASSWORD`

- Python ≥ 3
- Required packages: `pip install requests`
- fping from https://www.fping.org/

## Usage

Run the helper script to call any CloudPerf API:

```bash
python ~/.kiro/skills/cloudperf/cloudperf_api.py <function_name> [param1=value1 param2=value2 ...]
```

### Available Functions

1. **get_cityset** - 获取城市集合列表，id为集合ID，cityIds用于后续查询
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py cityset
   ```

2. **get_country** - 获取国家列表，不同cityset需重新请求
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py country cityset=27
   ```

3. **get_city** - 获取城市列表
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py city cityset=27 country=CN
   ```

4. **get_asn** - 获取ASN列表，city参数使用get_city返回的name字段，'A'代表所有城市
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py asn cityset=27 country=CN city=A
   ```

5. **get_performance** - 获取网络性能数据，src和dist为逗号分隔的cityIds
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py performance src=1213020226,1643985005 dist=3456789012
   ```

6. **get_rawdata** - 获取2000条原始数据，src和dist为逗号分隔的cityIds，返回数据里，dC 代表 "对应城市 - cityId", dA 代表 "对应ASN(asn号码)", dIP 代表 "起始IP - 结束IP"
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py rawdata src=1213020226,1643985005 dist=3456789012
   ```
7. **find_asninfo** - 通过关键字查询相关ASN信息
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py asninfo filter=Amazon
   ```

8. **find_ipinfo** - 查询指定ip的信息
   ```bash
   python ~/.kiro/skills/cloudperf/cloudperf_api.py ipinfo ip=100.2.3.4
   ```

## Workflow

典型查询流程：
1. `cityset` → 获取源节点集合（如 AWS Asia），记录 cityIds 作为 src
2. `country` → 指定 cityset 获取国家列表
3. `city` → 指定 cityset + country 获取城市
4. `asn` → 指定 cityset + country + city 获取 ASN，记录 cityIds 作为 dist（默认用 asnType='isp'）
5. `performance` → 用 src 和 dist 的 cityIds 查询性能数据

典型实时测试流程：
1. 先使用"典型查询流程"的 1-4 步，确定src和dist的cityIds，如果客户没有指定src，使用 us-east-1 作为src即可。
2. 如果dist里的cityIds很多，可以逐个cityIds进行请求，使用 `rawdata` 接口请求，获得多个 dIP 的 起始IP 和 结束IP
4. 合并重复的IP段，然后使用本机命令fping，发现IP段中的可ping ip，可以分组和并发进行测试，使用命令：fping -g {起始IP} {结束IP} -r 2 -a -q -X 100
5. 将上述的可ping ip，进行多次测试，如果ip过多，可以分组和并发进行测试，使用命令：fping -a -q -C 11 {对应多个可ping ip}
6. 总结汇总上述测试结果

## Output

All commands output JSON to stdout. Parse the JSON for structured data.
