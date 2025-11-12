# Test Organization

## Directory Structure

```
tests/
├── asio/                      # ASIO multi-channel tests
│   ├── README.md             # ASIO testing documentation
│   ├── check_asio.py         # Quick ASIO check
│   ├── check_device_channels.py
│   ├── test_asio_*.py        # Various ASIO tests
│   └── ...
│
├── autoloop/                  # Auto-loop functionality tests
│   ├── README.md             # Auto-loop testing documentation
│   ├── test_autoloop.py      # Comprehensive test script
│   ├── samples/              # Test sample files (user creates)
│   │   ├── short_sustain.wav
│   │   ├── medium_sustain.wav
│   │   ├── long_sustain.wav
│   │   ├── percussive.wav
│   │   └── noisy_sustain.wav
│   └── output/               # Test results (auto-created)
│
└── [integration tests]        # Existing integration tests
    ├── test_all.py
    ├── test_all.ps1
    └── ...
```

## Quick Start

### ASIO Tests

```bash
# Check ASIO availability
cd tests\asio
python check_asio.py

# Test direct recording
python test_asio_direct.py
```

### Auto-Loop Tests

```bash
# Create test samples first
cd tests\autoloop
python test_autoloop.py --create-samples

# Run all tests
python test_autoloop.py

# Run quick tests
python test_autoloop.py --quick
```

## Test Categories

### 1. ASIO Tests (tests/asio/)
- **Purpose**: Validate ASIO multi-channel functionality
- **Tests**: 9 test scripts
- **Status**: All validated ✅
- **Key Finding**: ASIO requires main-thread recording

### 2. Auto-Loop Tests (tests/autoloop/)
- **Purpose**: Comprehensive auto-loop testing
- **Tests**: 17 test cases across 6 groups
- **Prerequisites**: Test samples required
- **Coverage**:
  - Basic auto-loop
  - Minimum duration (% and seconds)
  - Fixed loop points
  - Crossfade (10-100ms)
  - Combined configurations
  - Edge cases

### 3. Integration Tests (tests/)
- **Purpose**: End-to-end workflow validation
- **Tests**: 17 tests across 6 groups
- **Status**: All passing ✅
- **Groups**: basic, velocity, roundrobin, combined, audio, metadata

## Running Tests

### All Integration Tests
```bash
python tests\test_all.py
```

### Quick Integration Tests
```bash
python tests\test_all.py --quick
```

### ASIO Tests
```bash
cd tests\asio
python test_asio_direct.py
```

### Auto-Loop Tests
```bash
cd tests\autoloop
python test_autoloop.py --quick
```

## Test Coverage

| Category | Tests | Status | Notes |
|----------|-------|--------|-------|
| Integration | 17 | ✅ Pass | All passing |
| ASIO | 9 | ✅ Validated | Threading fix working |
| Auto-Loop | 17 | ⏳ Pending | Requires samples |

## Creating Test Samples for Auto-Loop

See `tests/autoloop/README.md` for detailed instructions.

Quick method:
```bash
# Use existing Prophet 6 samples
copy output\prophet6_long_test\samples\prophet6_long_test_C4_v127_backup.wav ^
     tests\autoloop\samples\long_sustain.wav
```

## Future Test Additions

Potential additions:
- [ ] Unit tests (pytest-based)
- [ ] Performance benchmarks
- [ ] Multi-channel recording tests (4, 6, 8 channels)
- [ ] Different sample rates (48kHz, 96kHz)
- [ ] Different bit depths (16, 24, 32)
- [ ] Latency measurement tests
- [ ] MIDI timing tests
- [ ] SFZ validation tests (load in Sforzando)
