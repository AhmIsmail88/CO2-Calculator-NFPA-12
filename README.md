# CO2-Calculator-NFPA-12
CO₂ Total Flooding Calculator (NFPA 12) with a CustomTkinter GUI that calculates required CO₂ mass and cylinder count (100 lb / ~45.4 kg cylinders), and exports a professional PDF report including a preliminary piping schematic.

A simple desktop tool to estimate **CO₂ total flooding** agent quantity (based on NFPA 12-style flooding factors) using room dimensions and hazard category.  
Includes a **CustomTkinter GUI**, **cylinder count** (fixed **100 lb / ~45.4 kg** for v1), and **PDF report export** with a preliminary piping schematic.

> **Disclaimer:** This tool provides **conceptual/preliminary** calculations only. Always verify the final design against the applicable **NFPA 12 edition**, local codes, and AHJ requirements.

---

## Features
- CustomTkinter GUI (project + room inputs)
- Hazard selection (dropdown):
  - Surface Fire
  - Electrical Equipment
  - Marine Cargo
- Calculates:
  - Net room volume (m³ / ft³)
  - Base CO₂ required (lb)
  - Total CO₂ required with safety factor (lb / kg)
  - Main bank cylinders (100 lb each)
  - Optional **Reserve bank** (checkbox)
- Export a professional **PDF report** (tables + schematic)

---

## Requirements
- Python 3.9+ (recommended)
- Packages:
  - `customtkinter`
  - `reportlab`

Install:
```bash
pip install customtkinter reportlab
