# Sampling AUX Busses

## Overview
AutosamplerT supports up to 8 mono or 4 stereo AUX busses for advanced parallel sampling and monitoring. AUX busses can be used for both standard sampling and wavetable creation.

---

## AUX Output
- Each AUX output mirrors the main sampling input signal.
- When using ASIO, only the output channel number is required.
- Gain per AUX output channel is configurable in the main config.

**Config Example (AUX output, ASIO):**
```yaml
audio:
  aux_outputs:
    - channel: 1    # ASIO output channel number
      gain: -3.0
    - channel: 2
      gain: 0.0
```

---

## AUX Input
- Each AUX input can be assigned a name, channel, and gain in the YAML script.
- When using ASIO, only the input channel number is required.
- The name is used for the samples folder (e.g., `samples.distortion`).
- AUX inputs are sampled in parallel with the main input.
- All export formats (SFZ, QPAT, MAP, ADV) are generated for each AUX input.

**YAML Script Example (AUX input, ASIO):**
```yaml
aux_inputs:
  - name: "distortion"
    channel: 3
    gain: 2.0
  - name: "tape"
    channel: 4
    gain: 0.0
```

---

## Workflow Example
If you define 2 mono AUX channels:
- `distortion` (connected to a distortion pedal)
- `tape` (connected to a tape recorder)

You connect the AUX outputs to these devices, then connect their outputs to the AUX inputs.

**Result:**
- Standard samples in `samples/`
- Distortion samples in `samples.distortion/`
- Tape samples in `samples.tape/`
- Matching SFZ, QPAT, MAP, ADV files for each folder

---

## Behavior Summary
- AUX outputs mirror the main input, routed to the specified ASIO output channel.
- AUX inputs are sampled from the specified ASIO input channel, with gain applied.
- Each AUX input's samples are stored in their own folder.
- All export formats are generated for each AUX input.

---

## Notes
- When ASIO is active, device selection is not needed—only channel numbers are used for routing.
- AUX busses can be used for creative parallel processing, monitoring, and effect sampling.

---

*Last updated: January 24, 2026*
