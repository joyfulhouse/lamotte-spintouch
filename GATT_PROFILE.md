# SpinTouch BLE GATT Profile

Discovered via nRF Connect on 2025-11-28, updated 2025-11-29.

## Device Information

| Property | Value |
|----------|-------|
| Device Name | SpinTouch-0B2D1F |
| MAC Address | BB:BD:05:0B:2D:1F |
| Device ID | 3005 (0x0BBD) |

## Services

| Service | UUID |
|---------|------|
| Generic Access | `00001800-0000-1000-8000-00805f9b34fb` |
| Generic Attribute | `00001801-0000-1000-8000-00805f9b34fb` |
| **SpinTouch Service** | `00000000-0000-1000-8000-bbbd00000000` |

## SpinTouch Service Characteristics

| Name | UUID | Properties | Description |
|------|------|------------|-------------|
| Test Results | `00000000-0000-1000-8000-bbbd00000010` | Read | Main test results data (112 bytes) |
| Status | `00000000-0000-1000-8000-bbbd00000011` | Notify, Read | Status updates (0x01-0x0B) |
| Config 1 | `00000000-0000-1000-8000-bbbd00000012` | Read, Write | Configuration |
| Config 2 | `00000000-0000-1000-8000-bbbd00000013` | Read, Write | Configuration |
| Command 1 | `00000000-0000-1000-8000-bbbd00000020` | Write | Command input |
| Command Response | `00000000-0000-1000-8000-bbbd00000021` | Notify, Read | Command response (64 bytes) |
| Command 2 | `00000000-0000-1000-8000-bbbd00000022` | Write | Command input |
| Command 3 | `00000000-0000-1000-8000-bbbd00000023` | Write | Command input |
| Command 4 | `00000000-0000-1000-8000-bbbd00000030` | Write | Command input |
| Device Info | `00000000-0000-1000-8000-bbbd00000031` | Read | Device information (16 bytes) |
| Command 5 | `00000000-0000-1000-8000-bbbd00000040` | Write | Command input |
| Response 1 | `00000000-0000-1000-8000-bbbd00000041` | Notify, Read | Response data |
| Response 2 | `00000000-0000-1000-8000-bbbd00000050` | Notify, Read | Response data (12 bytes) |
| Response 3 | `00000000-0000-1000-8000-bbbd00000051` | Notify, Read | Response data (125 bytes) |
| Response 4 | `00000000-0000-1000-8000-bbbd00000052` | Notify, Read | Response data (125 bytes) |

## Test Results Data Format (Characteristic 0x...10)

The test results characteristic contains 112 bytes with the following structure:

### Header (Bytes 0-3)
```
01-02-03-05
```
Purpose unknown, possibly version/format identifier.

### Parameter Entries (Bytes 4-69)

Each entry is 6 bytes:
```
[param_id] [flags] [float32_le (4 bytes)]
```

**IMPORTANT**: The parameters present and their offsets vary by disk series! Parse by scanning for param_ids, not fixed offsets.

### Parameter ID Reference

| Param ID | Name | Unit | Disk Series |
|----------|------|------|-------------|
| 0x01 | Free Chlorine | ppm | All (when sanitizer=Chlorine) |
| 0x02 | Total Chlorine | ppm | All (when sanitizer=Chlorine) |
| 0x03 | Bromine | ppm | All (when sanitizer=Bromine) |
| 0x06 | pH | - | All |
| 0x07 | Total Alkalinity | ppm | All |
| 0x08 | Calcium Hardness (High Range) | ppm | 204, 304 (0-1200 ppm) |
| 0x0A | Cyanuric Acid | ppm | All |
| 0x0B | Iron | ppm | 203, 303 (not on 204, 304) |
| 0x0C | Copper | ppm | All (0-3.0 ppm) |
| 0x0D | Phosphate/Borate | ppm/ppb | 203/204=Phosphate, 303/304=Borate |
| 0x0E | Borate | ppm | 203, 204 |
| 0x0F | Calcium Hardness (Standard) | ppm | 203, 303, 402 (0-800 ppm) |
| 0x10 | Salt | ppm | All (0-5000 ppm) |
| 0x11 | Unknown | - | All (always 0?) |

### Disk Series Summary

| Disk | Name | Param 0x0D | Calcium Param | Has Iron |
|------|------|------------|---------------|----------|
| 203 | Chlorine/Bromine + Phosphate | Phosphate | 0x0F (800 ppm) | Yes |
| 204 | High Range + Phosphate | Phosphate | 0x08 (1200 ppm) | No |
| 303 | Chlorine/Bromine + Borate | Borate | 0x0F (800 ppm) | Yes |
| 304 | High Range + Borate | Borate | 0x08 (1200 ppm) | No |
| 402 | Biguanide | N/A | 0x0F (800 ppm) | Yes |

**Notes**:
- All disks test FC, TC, Bromine, pH, Alkalinity, CYA, Copper, Salt (except 402 has no sanitizer)
- Sanitizer type (Chlorine vs Bromine) is a user selection, not disk-dependent
- 203/303 vs 204/304: Standard vs High Range calcium/salt
- 203/204 vs 303/304: Phosphate vs Borate

### Flags Interpretation
- `0x00` = Standard reading
- `0x01` = Low range / alternative scale
- `0x02` = Normal reading

### Timestamp (Bytes 76-81)
```
YY-MM-DD-HH-MM-SS (binary, not BCD)
```
Example: `19-0B-1D-0C-19-1A` = 2025-11-29 12:25:26

### Metadata (Bytes 82+)

After the timestamp, there's a metadata section containing test info and param_id list.

## Captured Test Data

### Bromine 203 (2025-11-29)
```
01-02-03-05-03-02-9D-46-61-3D-06-01-9A-99-C9-40-07-00-00-00-00-00-
0F-00-00-00-00-00-0C-01-46-16-71-3D-0B-01-00-00-00-00-0E-00-00-00-
00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-
00-00-00-00-00-00-00-00-00-00-19-0B-1D-0C-27-3A-...
```

| Parameter | Param ID | Value | Unit |
|-----------|----------|-------|------|
| Bromine | 0x03 | 0.055 | ppm |
| pH | 0x06 | 6.30 | - |
| Total Alkalinity | 0x07 | 0.00 | ppm |
| Calcium Hardness | 0x0F | 0.00 | ppm |
| Copper | 0x0C | 0.059 | ppm |
| Iron | 0x0B | 0.00 | ppm |
| Borate | 0x0E | 0.00 | ppm |

**Note**: Bromine disk has param 0x03 (Bromine) instead of 0x01/0x02 (Chlorine)!

### Salt 204 (2025-11-29)
```
01-02-03-05-01-02-00-00-00-00-02-02-00-00-00-00-11-02-00-00-00-00-
06-01-9A-99-C9-40-07-00-00-00-00-00-08-00-00-00-00-00-0A-00-00-00-
A0-40-0C-01-4B-C3-33-3D-0E-00-00-00-00-00-10-00-0D-6F-E6-42-...
```

| Parameter | Param ID | Value | Unit |
|-----------|----------|-------|------|
| Free Chlorine | 0x01 | 0.00 | ppm |
| Total Chlorine | 0x02 | 0.00 | ppm |
| pH | 0x06 | 6.30 | - |
| Total Alkalinity | 0x07 | 0.00 | ppm |
| Calcium Hardness | 0x08 | 0.00 | ppm |
| Cyanuric Acid | 0x0A | 5.00 | ppm |
| Copper | 0x0C | 0.044 | ppm |
| Borate | 0x0E | 0.00 | ppm |

### Salt 303 (2025-10-11)
```
01-02-03-05-01-02-64-B7-9A-40-02-02-64-B7-9A-40-11-02-00-00-00-00-
06-01-20-B6-EF-40-07-00-FD-5C-EE-42-0F-00-B5-96-02-42-0A-00-A2-F6-
50-42-0C-01-C6-9D-8D-3E-0B-01-09-47-F0-3D-0D-00-7C-8F-30-42-10-00-
B1-FC-39-45-...
```

| Parameter | Param ID | Value | Unit |
|-----------|----------|-------|------|
| Free Chlorine | 0x01 | 4.83 | ppm |
| Total Chlorine | 0x02 | 4.83 | ppm |
| pH | 0x06 | 7.49 | - |
| Total Alkalinity | 0x07 | 119.18 | ppm |
| Calcium Hardness | 0x0F | 32.65 | ppm |
| Cyanuric Acid | 0x0A | 52.24 | ppm |
| Copper | 0x0C | 0.28 | ppm |
| Iron | 0x0B | 0.12 | ppm |
| Borate | 0x0D | 44.14 | ppm |
| Salt | 0x10 | 2976 | ppm |

### Chlorine 304 (2025-11-29)
```
01-02-03-05-01-02-00-90-5A-41-02-02-00-90-5A-41-11-02-00-00-00-00-
06-01-B7-4F-F4-40-07-00-F1-3A-F8-42-0F-00-A4-13-97-43-0A-00-EA-24-
31-42-0C-01-3E-5F-0A-40-0B-01-14-27-FD-3D-0D-00-D5-66-37-42-10-00-
03-98-52-45-...
```

| Parameter | Param ID | Value | Unit |
|-----------|----------|-------|------|
| Free Chlorine | 0x01 | 13.66 | ppm |
| Total Chlorine | 0x02 | 13.66 | ppm |
| pH | 0x06 | 7.64 | - |
| Total Alkalinity | 0x07 | 124.12 | ppm |
| Calcium Hardness | 0x0F | 302.15 | ppm |
| Cyanuric Acid | 0x0A | 44.29 | ppm |
| Copper | 0x0C | 2.16 | ppm |
| Iron | 0x0B | 0.12 | ppm |
| Borate | 0x0D | 45.85 | ppm |
| Salt | 0x10 | 3370 | ppm |

## Key Findings

1. **Param ID determines chemical type**: The param_id (first byte of each 6-byte entry) identifies what chemical is being measured.

2. **Chlorine vs Bromine**:
   - Chlorine disks (303, 304) use param 0x01 (Free Chlorine) and 0x02 (Total Chlorine)
   - Bromine disks (203) use param 0x03 (Bromine) - no chlorine params!

3. **Different disks = different parameters**: Each disk series tests different chemicals:
   - Disk 203 (Bromine): 0x03 (Br), 0x0E (Borate), 0x0F (Ca), 0x0B (Fe)
   - Disk 204 (Salt): 0x08 (Ca), 0x0E (Borate), no Fe
   - Disk 303/304 (Chlorine): 0x01/02 (FC/TC), 0x0F (Ca), 0x0B (Fe), 0x0D (Borate)

4. **Calcium Hardness has two param_ids**:
   - 0x08 = Calcium on disk 204
   - 0x0F = Calcium on disks 203, 303, 304

5. **Borate has two param_ids**:
   - 0x0D = Borate on disks 303, 304 (can also be Phosphate on some disks)
   - 0x0E = Borate on disks 203, 204

6. **Parsing recommendation**: Parse by scanning the param_id at each 6-byte boundary, not by fixed offset. This ensures compatibility with all disk series.

## Device Info Data Format (Characteristic 0x...31)

16 bytes:
```
BD-0B-00-00-01-FF-00-01-3A-01-00-00-00-00-00-00
```

| Offset | Length | Description |
|--------|--------|-------------|
| 0-1 | 2 | Device ID (little-endian): 0x0BBD = 3005 |
| 4 | 1 | Firmware major version |
| 5 | 1 | Firmware minor version |

## Status Notifications (Characteristic 0x...11)

The status characteristic sends single-byte notifications:

| Value | Meaning |
|-------|---------|
| 0x01 | Initializing |
| 0x02 | Ready |
| 0x03 | Testing in progress |
| 0x04 | Test complete |
| 0x05 | Error |
| 0x06 | Idle |
| 0x07 | ? (seen during bromine test) |
| 0x08 | ? (seen during bromine test) |
| 0x09 | ? (seen during bromine test) |
| 0x0B | ? (seen during chlorine test) |

## Official LaMotte SpinDisk Specifications

Reference: [waterlinkspintouch.com/disks.html](https://www.waterlinkspintouch.com/disks.html), [lamotte.com](https://lamotte.com)

### 10-Parameter Single-Use Disks

| Order Code | Series | Name | Key Difference |
|------------|--------|------|----------------|
| 4329-H/J | 203 | Chlorine/Bromine + Phosphate | Has Phosphate, has Iron |
| 4330-H/J | 303 | Chlorine/Bromine + Borate | Has Borate (0x0D), has Iron |
| 4349-H/J | 204 | High Range + Phosphate | High range Ca/Salt, has Phosphate |
| 4350-H/J | 304 | High Range + Borate | High range Ca/Salt, has Borate |
| 4331-H/J | 402 | Biguanide | No chlorine/bromine, has Biguanide |

### Series 203 (4329) - Chlorine/Bromine + Phosphate

| Parameter | Range |
|-----------|-------|
| Free Chlorine (DPD) | 0-15 ppm |
| Total Chlorine (DPD) | 0-15 ppm |
| Bromine (DPD) | 0-33 ppm |
| pH | 6.4-8.6 |
| Calcium Hardness | 0-800 ppm |
| Total Alkalinity | 0-250 ppm |
| Cyanuric Acid | 5-150 ppm |
| Copper | 0-3.0 ppm |
| Iron | 0-3.0 ppm |
| Salt | 0-5000 ppm |
| Phosphate | 0-2000 ppb |

### Series 303 (4330) - Chlorine/Bromine + Borate

| Parameter | Range |
|-----------|-------|
| Free Chlorine (DPD) | 0-15 ppm |
| Total Chlorine (DPD) | 0-15 ppm |
| Bromine (DPD) | 0-33 ppm |
| pH | 6.4-8.6 |
| Calcium Hardness | 0-800 ppm |
| Total Alkalinity | 0-250 ppm |
| Cyanuric Acid | 5-150 ppm |
| Copper | 0-3.0 ppm |
| Iron | 0-3.0 ppm |
| Salt | 0-5000 ppm |
| Borate | 0-60 ppm |

### Series 204 (4349) - High Range + Phosphate

| Parameter | Range |
|-----------|-------|
| Free Chlorine (DPD) | 0-15 ppm |
| Total Chlorine (DPD) | 0-15 ppm |
| Bromine (DPD) | 0-33 ppm |
| pH | 6.4-8.6 |
| Total Hardness | 0-1200 ppm |
| Total Alkalinity | 0-250 ppm |
| Cyanuric Acid | 5-150 ppm |
| Copper | 0-3.0 ppm |
| Salt | 0-5000 ppm |
| Phosphate | 0-2000 ppb |

**Note**: No Iron test. Uses param 0x08 for Calcium (high range).

### Series 304 (4350) - High Range + Borate

| Parameter | Range |
|-----------|-------|
| Free Chlorine (DPD) | 0-15 ppm |
| Total Chlorine (DPD) | 0-15 ppm |
| Bromine (DPD) | 0-33 ppm |
| pH | 6.4-8.6 |
| Total Hardness | 0-1200 ppm |
| Total Alkalinity | 0-250 ppm |
| Cyanuric Acid | 5-150 ppm |
| Copper | 0-3.0 ppm |
| Salt | 0-5000 ppm |
| Borate | 0-80 ppm |

**Note**: No Iron test. Uses param 0x08 for Calcium (high range).

### Series 402 (4331) - Biguanide

| Parameter | Range |
|-----------|-------|
| pH | 6.4-8.6 |
| Calcium Hardness | 0-800 ppm |
| Total Alkalinity | 0-250 ppm |
| Copper | 0-3.0 ppm |
| Iron | 0-3.0 ppm |
| Borate | 0-80 ppm |
| Biguanide | 0-70 ppm |
| Biguanide Shock | 0-250 ppm |

**Note**: No chlorine/bromine tests - for Biguanide (Baquacil) pools only.

### 3-Parameter Triple-Use Disks

| Order Code | Series | Parameters |
|------------|--------|------------|
| 4334-H | 501 | Free Chlorine, Total Chlorine, pH |
| 4335-H | 601 | Free Chlorine, pH, Alkalinity |

These disks can be used 3 times each and deliver results in ~30 seconds.

## ESPHome Integration

See `esphome/spintouch.yaml` for the ESPHome configuration.

Key points:
1. Connect to service `00000000-0000-1000-8000-bbbd00000000`
2. Read characteristic `00000000-0000-1000-8000-bbbd00000010` for test results
3. Enable notifications on `00000000-0000-1000-8000-bbbd00000011` for status
4. Parse the 6-byte entries by scanning param_ids to extract float values
