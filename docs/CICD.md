# CI/CD Pipelines Documentation

This document describes the GitHub Actions workflows for continuous integration and deployment of the Redis cache hardware design.

## Overview

The project includes two main CI/CD pipelines:

1. **RTL Frontend Pipeline** - Runs on every push
2. **Librelane Full Pipeline** - Runs on PR to main

## RTL Frontend Pipeline

**File:** `.github/workflows/rtl-frontend.yml`

**Triggers:**
- Push to any branch
- Pull requests to any branch

**Purpose:** Rapid feedback on RTL design quality, syntax, and basic functionality.

### Jobs

#### 1. RTL Design Check
- **Purpose:** Validate Verilog syntax and design quality
- **Steps:**
  - Checkout code
  - Install Icarus Verilog
  - Run syntax checks with `make syntax`
  - Optional: Run Verilator linting

#### 2. Simulation
- **Purpose:** Execute CoCoTB tests
- **Steps:**
  - Setup Python 3.11 environment
  - Install test dependencies
  - Run test suite with `make test`
  - Upload test results and waveforms

#### 3. Verification
- **Purpose:** Code quality and coverage analysis
- **Steps:**
  - Run Python linting
  - Generate coverage reports
  - Validate test completeness

#### 4. Summary
- **Purpose:** Aggregate results and report status
- **Steps:**
  - Collect job statuses
  - Report overall pipeline health

### Expected Duration
- Total: ~5-10 minutes
- RTL Check: 1-2 minutes
- Simulation: 2-5 minutes
- Verification: 1-2 minutes

### Artifacts
- Test results (XML)
- Waveforms (VCD files)
- Coverage reports

## Librelane Full Pipeline

**File:** `.github/workflows/librelane-pipeline.yml`

**Triggers:**
- Pull requests to `main` branch

**Purpose:** Complete ASIC design flow from RTL to GDSII.

### Jobs

#### 1. Setup
- Install dependencies
- Cache build artifacts
- Prepare environment

#### 2. RTL Synthesis
- **Tool:** Yosys (open-source) or commercial tools
- **Steps:**
  - Read Verilog sources
  - Technology mapping
  - Generate gate-level netlist
- **Outputs:**
  - Synthesized netlist (.v)
  - Synthesis report

#### 3. Place and Route
- **Tool:** nextpnr or commercial P&R tools
- **Steps:**
  - Floorplanning
  - Placement optimization
  - Routing
  - Clock tree synthesis
- **Outputs:**
  - Layout database
  - P&R report

#### 4. Static Timing Analysis (STA)
- **Purpose:** Verify timing constraints
- **Checks:**
  - Setup time violations
  - Hold time violations
  - Clock skew analysis
  - Critical path identification
- **Outputs:**
  - Timing reports
  - Slack analysis

#### 5. Design Rule Check (DRC)
- **Purpose:** Verify physical design rules
- **Checks:**
  - Spacing violations
  - Width violations
  - Antenna effects
  - Density requirements
- **Outputs:**
  - DRC report
  - Violation markers

#### 6. Layout vs Schematic (LVS)
- **Purpose:** Verify layout matches schematic
- **Checks:**
  - Net connectivity
  - Device matching
  - Topology verification
- **Outputs:**
  - LVS report
  - Comparison results

#### 7. Parasitic Extraction
- **Purpose:** Extract RC parasitics from layout
- **Outputs:**
  - SPEF/DSPF files
  - Parasitic database

#### 8. Post-Layout Simulation
- **Purpose:** Verify with extracted parasitics
- **Steps:**
  - Back-annotate parasitics
  - Run functional tests
  - Verify timing with real delays

#### 9. Power Analysis
- **Purpose:** Estimate power consumption
- **Analysis:**
  - Dynamic power
  - Static (leakage) power
  - Peak current
  - IR drop analysis

#### 10. Generate GDSII
- **Purpose:** Create final layout file
- **Outputs:**
  - GDSII stream file (.gds)
  - Layout metadata

#### 11. Documentation
- **Purpose:** Generate design documentation
- **Outputs:**
  - Datasheet
  - Design report
  - Area/timing/power summary

#### 12. Pipeline Summary
- **Purpose:** Aggregate all results
- **Failure Conditions:**
  - Synthesis errors
  - Timing violations
  - DRC/LVS failures
  - Critical issues in any stage

### Expected Duration
- Total: ~30-60 minutes (depends on design size and tools)
- Synthesis: 5-10 minutes
- P&R: 10-20 minutes
- Verification stages: 15-30 minutes

### Artifacts
- Gate-level netlist
- Layout database
- GDSII file
- All reports (timing, power, DRC, LVS)
- Documentation

## Configuration

### Environment Variables

```yaml
# RTL Frontend
SIM: icarus              # Simulator choice
PYTHON: python3          # Python executable

# Librelane Pipeline
PDK: sky130              # Process Design Kit (to be configured)
CORNER: typical          # PVT corner
FREQ: 100MHz            # Target frequency
```

### Secrets (to be configured)

```
# For commercial tools (if needed)
SYNOPSYS_LICENSE
CADENCE_LICENSE
MENTOR_LICENSE
```

## Local Testing

### Test RTL Frontend Locally

```bash
# Syntax check
make syntax

# Run tests
make test

# Linting
make lint
```

### Simulate Librelane Pipeline Steps

```bash
# Synthesis (requires Yosys)
yosys -p "read_verilog src/**/*.v; synth -top redis_cache_top"

# Run specific checks
make syntax
make test
```

## Customization

### Adding New Tests

1. Create test file in `test/`
2. Add make target in `Makefile`
3. Tests automatically run in CI

### Adding Librelane Stages

Edit `.github/workflows/librelane-pipeline.yml`:

```yaml
new-stage:
  name: New Stage
  runs-on: ubuntu-latest
  needs: previous-stage
  
  steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Run stage
      run: |
        # Your commands here
```

### Tool Configuration

Configure tools via:
- Environment variables
- Configuration files in project root
- Tool-specific scripts in `scripts/` directory

## Monitoring

### Status Badges

Add to README:

```markdown
![RTL Frontend](https://github.com/USER/REPO/actions/workflows/rtl-frontend.yml/badge.svg)
![Librelane](https://github.com/USER/REPO/actions/workflows/librelane-pipeline.yml/badge.svg)
```

### Notifications

Configure in GitHub repository settings:
- Email notifications
- Slack integration
- Custom webhooks

## Troubleshooting

### Common Issues

**Syntax errors:**
```bash
# Check locally first
make syntax
```

**Test failures:**
```bash
# Run tests locally with verbose output
pytest -v test/
```

**Missing dependencies:**
```bash
# Reinstall
make install
```

**Tool not found:**
- Check tool installation in workflow
- Verify tool is in PATH
- Check license availability

### Getting Help

1. Check workflow logs in GitHub Actions
2. Run locally to reproduce
3. Check tool-specific documentation
4. Review error messages carefully

## Future Enhancements

- [ ] Add formal verification stage
- [ ] Implement automated regression testing
- [ ] Add performance benchmarking
- [ ] Generate HTML reports
- [ ] Integrate with external dashboards
- [ ] Add artifact archiving strategy
- [ ] Implement PDK-specific configurations

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Yosys Manual](https://yosyshq.net/yosys/)
- [Sky130 PDK](https://github.com/google/skywater-pdk)
- [OpenLane Flow](https://github.com/The-OpenROAD-Project/OpenLane)
