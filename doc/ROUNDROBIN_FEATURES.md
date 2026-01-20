# Round-Robin Features in AutosamplerT

Based on analysis of test files and Waldorf MAP format discoveries.

## Round-Robin Types Discovered

### 1. Standard Round-Robin
- **File**: `looprule roundrobin.map`  
- **Behavior**: Sequential playback through variations
- **YAML**: `roundrobin_layers: 3`
- **MIDI Control**: Per-layer NRPN or CC messages

### 2. Random Round-Robin  
- **File**: `looprule random.map`
- **Behavior**: Random selection of variations
- **Usage**: Adds unpredictability to repeated notes
- **Implementation**: Hardware-controlled selection algorithm

### 3. Reverse Round-Robin
- **File**: `looprule reverse roundrobin.map` 
- **Behavior**: Plays variations in reverse order
- **Pattern**: 3→2→1→3→2→1...
- **Use Case**: Special articulation sequences

## Configuration

### YAML Script Setup
```yaml
sampling:
  velocity_layers: 1      # Single velocity layer
  roundrobin_layers: 3    # 3 round-robin variations

sampling_midi:
  roundrobin_midi_control:
    - layer: 0
      nrpn_messages: {45: 0}     # First variation
    - layer: 1  
      nrpn_messages: {45: 55}    # Second variation
    - layer: 2
      nrpn_messages: {45: 110}   # Third variation
```

### Per-Layer MIDI Control
Each round-robin layer can have different MIDI settings:
- **NRPN Messages**: Device-specific parameters
- **CC Messages**: Standard MIDI controllers  
- **Program Changes**: Different patches per layer
- **SysEx**: Complex parameter changes

## File Naming Convention

AutosamplerT uses consistent naming for round-robin samples:
```
MySynth_60_v127_rr0.wav  # Note 60, Velocity 127, Round-robin 0
MySynth_60_v127_rr1.wav  # Note 60, Velocity 127, Round-robin 1  
MySynth_60_v127_rr2.wav  # Note 60, Velocity 127, Round-robin 2
```

## Multi-Layer Combinations

### Velocity + Round-Robin
```yaml
sampling:
  velocity_layers: 3      # Soft, Medium, Hard
  roundrobin_layers: 2    # 2 variations per velocity

sampling_midi:
  velocity_midi_control:
    - layer: 0
      cc_messages: {7: 32}    # Soft layer
    - layer: 1
      cc_messages: {7: 80}    # Medium layer  
    - layer: 2
      cc_messages: {7: 127}   # Hard layer
      
  roundrobin_midi_control:
    - layer: 0
      nrpn_messages: {45: 0}     # First variation
    - layer: 1
      nrpn_messages: {45: 64}    # Second variation
```

**Result**: 6 total samples per note (3 velocities × 2 round-robin)

## Hardware Implementation

### Waldorf MAP Format
Round-robin layers are exported as separate groups in the MAP/QPAT file:
- **Group 1**: Velocity layer 1, Round-robin 1
- **Group 2**: Velocity layer 1, Round-robin 2  
- **Group 3**: Velocity layer 1, Round-robin 3

### Sample Selection Algorithm
The hardware determines which sample to play based on:
1. **Key pressed**: Selects from key range
2. **Velocity**: Selects velocity layer
3. **Round-robin state**: Selects variation within layer
4. **Algorithm**: Sequential, random, or reverse

## Common Terminology Confusion

### "Loop Ping Pong" ≠ Audio Loop
- **Filename**: `looppingpong.map`
- **Actual meaning**: Round-robin ping-pong algorithm
- **NOT**: Audio loop direction (forward/reverse)
- **Behavior**: Alternates 1→2→3→2→1→2→3...

### "Loop Direction" vs Round-Robin Direction  
- **Audio Loop Direction**: Column 14 in MAP format
- **Round-Robin Direction**: Algorithm selection method
- **Different parameters**: Control separate behaviors

## Use Cases

### Musical Applications
1. **Natural Variation**: Acoustic instruments with slight differences
2. **Articulations**: Different playing techniques per variation  
3. **Dynamics**: Subtle volume differences between layers
4. **Timbral Changes**: Filter sweeps or modulation per layer

### Sound Design
1. **Randomization**: Unpredictable sonic textures
2. **Sequences**: Programmed patterns via reverse round-robin
3. **Evolution**: Gradually changing sounds over repetitions
4. **Complexity**: Multi-dimensional sample selection

## Testing Round-Robin

### Verification Method
1. **Load MAP file** with multiple round-robin layers
2. **Play same key repeatedly** 
3. **Listen for variations** in each trigger
4. **Verify algorithm**: Sequential, random, or reverse pattern

### Expected Behavior
- **Sequential**: A→B→C→A→B→C...
- **Random**: A→C→A→B→C→B... (unpredictable)
- **Reverse**: A→B→C→B→A→B→C... (ping-pong)

---

*Documentation: Round-Robin Features*  
*Date: January 16, 2026*  
*Status: Verified through hardware testing and file analysis*