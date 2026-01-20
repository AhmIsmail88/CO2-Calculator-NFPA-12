import math
from datetime import datetime

# -----------------------------
# Optional dependency checks
# -----------------------------
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
except Exception as e:
    raise SystemExit(
        "Missing GUI dependencies. Install: pip install customtkinter\n"
        "Also ensure tkinter is available (on Linux: sudo apt-get install python3-tk)\n"
        f"Error: {e}"
    )

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable
    from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String
    from reportlab.graphics import renderPDF
except Exception as e:
    raise SystemExit(
        "Missing PDF dependencies. Install: pip install reportlab\n"
        f"Error: {e}"
    )

# =============================
# NFPA 12 (based on your logic)
# =============================

HAZARDS = [
    "Surface Fire",
    "Electrical Equipment",
    "Marine Cargo",
]

CYLINDER_SIZE_LB = 100.0   # v1 fixed (≈45.4 kg)
LB_TO_KG = 0.453592
M3_TO_FT3 = 35.3147
UNIT_OPTIONS = [
    ("Meters (m)", "m", 1.0),
    ("Centimeters (cm)", "cm", 0.01),
    ("Millimeters (mm)", "mm", 0.001),
    ("Feet (ft)", "ft", 0.3048),
    ("Inches (in)", "in", 0.0254),
]
UNIT_LABEL_TO_UNIT = {label: unit for label, unit, _ in UNIT_OPTIONS}
UNIT_TO_M = {unit: factor for _, unit, factor in UNIT_OPTIONS}


def calculate_co2(system_data: dict) -> dict:
    """
    Pure calculation engine (no GUI / no printing).
    Uses the same flooding-factor branching you wrote.
    Includes: include_reserve checkbox to compute total cylinders.
    """
    L, W, H = system_data["dimensions_m"]

    if any(v <= 0 for v in (L, W, H)):
        raise ValueError("Room dimensions must be positive numbers.")

    volume_m3 = L * W * H
    volume_ft3 = volume_m3 * M3_TO_FT3

    hazard = system_data["hazard"]
    safety_factor = float(system_data.get("safety_factor", 1.1))
    if safety_factor <= 0:
        raise ValueError("Safety factor must be > 0.")

    cylinder_size_lb = float(system_data.get("cylinder_size_lb", CYLINDER_SIZE_LB))
    if cylinder_size_lb <= 0:
        raise ValueError("Cylinder size must be > 0.")

    base_lb = _base_co2_lb(volume_ft3, hazard)
    total_lb = base_lb * safety_factor
    total_kg = total_lb * LB_TO_KG

    cyl_main = math.ceil(total_lb / cylinder_size_lb)

    include_reserve = bool(system_data.get("include_reserve", True))
    cyl_reserve = cyl_main if include_reserve else 0
    cyl_total = cyl_main + cyl_reserve

    return {
        "volume_m3": volume_m3,
        "volume_ft3": volume_ft3,
        "base_lb": base_lb,
        "total_lb": total_lb,
        "total_kg": total_kg,
        "cylinders_main": cyl_main,
        "cylinders_reserve": cyl_reserve,
        "cylinders_total": cyl_total,
        "include_reserve": include_reserve,
        "cylinder_size_lb": cylinder_size_lb,
        "cylinder_size_kg": cylinder_size_lb * LB_TO_KG,
    }


def _base_co2_lb(volume_ft3: float, hazard: str) -> float:
    # SAME branching you implemented
    if hazard == "Surface Fire":
        if volume_ft3 <= 140:
            return volume_ft3 / 14
        if volume_ft3 <= 500:
            return volume_ft3 / 15
        if volume_ft3 <= 1600:
            return volume_ft3 / 16
        if volume_ft3 <= 4500:
            return volume_ft3 / 18
        if volume_ft3 <= 50000:
            return volume_ft3 / 20
        return volume_ft3 / 22

    if hazard == "Electrical Equipment":
        if volume_ft3 <= 2000:
            return volume_ft3 / 10
        return max(200, volume_ft3 / 12)

    if hazard == "Marine Cargo":
        return volume_ft3 / 30

    raise ValueError("Invalid hazard selection.")


# =============================
# Schematic (Vector) - Isometric-like
# =============================

class DrawingFlowable(Flowable):
    """Wrap a reportlab.graphics Drawing so it can be inserted into Platypus story safely."""
    def __init__(self, drawing: Drawing):
        super().__init__()
        self.drawing = drawing
        self.width = drawing.width
        self.height = drawing.height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        renderPDF.draw(self.drawing, self.canv, 0, 0)


def build_isometric_schematic(system_data: dict, results: dict, width=520, height=330) -> Drawing:
    """
    Preliminary piping isometric-style schematic similar to the sample image:
    - Cylinder at base + axes N/E/S/W
    - Vertical pipe then sloped run to a nozzle tag
    - Labels: cylinder, valve (VOA), nozzle tag
    """
    d = Drawing(width, height)

    # Colors (keep close to the look in your image)
    axis_color = colors.Color(0.15, 0.25, 0.65)   # blue-ish
    pipe_color = colors.black
    fitting_color = colors.green
    cyl_color = colors.red

    # Origin (axes crossing) near bottom-left/center
    ox = width * 0.33
    oy = height * 0.22

    # Axes lines
    axis_len = 170
    # N (upper-left)
    d.add(Line(ox, oy, ox - axis_len * 0.70, oy + axis_len * 0.55, strokeColor=axis_color, strokeWidth=1))
    d.add(String(ox - axis_len * 0.73, oy + axis_len * 0.58, "N", fontSize=9, fillColor=axis_color))
    # E (upper-right)
    d.add(Line(ox, oy, ox + axis_len * 0.80, oy + axis_len * 0.45, strokeColor=axis_color, strokeWidth=1))
    d.add(String(ox + axis_len * 0.83, oy + axis_len * 0.48, "E", fontSize=9, fillColor=axis_color))
    # S (lower-right)
    d.add(Line(ox, oy, ox + axis_len * 0.55, oy - axis_len * 0.50, strokeColor=axis_color, strokeWidth=1))
    d.add(String(ox + axis_len * 0.58, oy - axis_len * 0.55, "S", fontSize=9, fillColor=axis_color))
    # W (lower-left)
    d.add(Line(ox, oy, ox - axis_len * 0.70, oy - axis_len * 0.40, strokeColor=axis_color, strokeWidth=1))
    d.add(String(ox - axis_len * 0.74, oy - axis_len * 0.45, "W", fontSize=9, fillColor=axis_color))

    # Cylinder (single drawn, annotate xN)
    cyl_w, cyl_h = 34, 82
    cyl_x = ox - cyl_w / 2
    cyl_y = oy + 6  # above origin
    d.add(Rect(cyl_x, cyl_y, cyl_w, cyl_h, strokeColor=cyl_color, strokeWidth=1.2, fillColor=None, rx=6, ry=6))
    # top cap (approx)
    d.add(Line(cyl_x + 5, cyl_y + cyl_h, cyl_x + cyl_w - 5, cyl_y + cyl_h, strokeColor=cyl_color, strokeWidth=1.2))
    # label
    cyl_main = results.get("cylinders_main", 1)
    cyl_label = f"{cyl_main} x {results['cylinder_size_lb']:.0f} lb Cylinders (~{results['cylinder_size_kg']:.1f} kg)"
    d.add(String(ox - 65, cyl_y - 16, cyl_label, fontSize=8))

    # Valve (VOA) and outlet point
    valve_x = ox
    valve_y = cyl_y + cyl_h + 10
    d.add(Circle(valve_x, valve_y, 4, strokeColor=pipe_color, strokeWidth=1, fillColor=None))
    d.add(String(valve_x + 8, valve_y - 3, "20mm VOA", fontSize=8))

    # Pipe route points (mimic the sample shape)
    p0 = (valve_x, valve_y)                 # at valve
    p1 = (valve_x, valve_y + 95)            # vertical up
    p2 = (p1[0] + 250, p1[1] + 90)          # sloped to the right/up
    p3 = (p2[0], p2[1] - 18)                # small drop near nozzle
    nozzle = (p3[0] + 12, p3[1])            # nozzle position

    # Pipe segments
    d.add(Line(p0[0], p0[1], p1[0], p1[1], strokeColor=pipe_color, strokeWidth=1))
    d.add(Line(p1[0], p1[1], p2[0], p2[1], strokeColor=pipe_color, strokeWidth=1))
    d.add(Line(p2[0], p2[1], p3[0], p3[1], strokeColor=pipe_color, strokeWidth=1))
    d.add(Line(p3[0], p3[1], nozzle[0], nozzle[1], strokeColor=pipe_color, strokeWidth=1))

    # Fittings markers (green)
    for pt in (p0, p1, p2):
        d.add(Circle(pt[0], pt[1], 3, strokeColor=fitting_color, strokeWidth=1, fillColor=None))

    # Node numbers similar to image (5..8)
    d.add(String(p0[0] - 10, p0[1] - 12, "5", fontSize=8, fillColor=colors.black))
    d.add(String((p0[0] + p1[0]) / 2 - 8, (p0[1] + p1[1]) / 2, "6", fontSize=8))
    d.add(String(p1[0] - 10, p1[1] - 12, "7", fontSize=8))
    d.add(String(p2[0] - 10, p2[1] - 12, "8", fontSize=8))

    # Nozzle symbol + tag
    d.add(Circle(nozzle[0], nozzle[1], 4, strokeColor=pipe_color, strokeWidth=1, fillColor=None))
    d.add(Line(nozzle[0] - 6, nozzle[1], nozzle[0] + 6, nozzle[1], strokeColor=pipe_color, strokeWidth=1))
    d.add(Line(nozzle[0], nozzle[1] - 6, nozzle[0], nozzle[1] + 6, strokeColor=pipe_color, strokeWidth=1))
    nozzle_tag = system_data.get("nozzle_tag", "E1-N1")
    d.add(String(nozzle[0] + 10, nozzle[1] - 3, nozzle_tag, fontSize=8))

    # Title (small)
    d.add(String(10, height - 18, "Preliminary CO2 Piping Schematic (Conceptual)", fontSize=9))

    return d


# =============================
# PDF Report (Professional)
# =============================

def export_pdf(path: str, system_data: dict, results: dict) -> None:
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    title = "<font color='#1F4E79'>CO2 Total Flooding Calculator Report (Conceptual) – NFPA 12</font>"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 10))

    # Project info
    proj = [
        ["Field", "Value"],
        ["Project Name", system_data.get("project_name", "")],
        ["Room Name", system_data.get("room_name", "")],
        ["Input Units", system_data.get("dimension_unit_label", "m")],
        ["Hazard Type", system_data.get("hazard", "")],
        ["Safety Factor", str(system_data.get("safety_factor", 1.1))],
        ["Cylinder Size", f"{results['cylinder_size_lb']:.0f} lb (~{results['cylinder_size_kg']:.1f} kg)"],
        ["Reserve Bank Included", "Yes" if results.get("include_reserve", True) else "No"],
        ["Nozzle Tag (schematic)", system_data.get("nozzle_tag", "E1-N1")],
    ]
    story.append(Paragraph("Project Information", styles["Heading2"]))
    story.append(_styled_table(proj, col_widths=[170, 330], has_header=True))
    story.append(Spacer(1, 10))

    # Inputs
    dims_original = system_data["dimensions_original"]
    unit_label = system_data.get("dimension_unit_label", "m")
    L, W, H = system_data["dimensions_m"]
    inputs = [
        ["Dimension", "Entered Value", "Meters (m)"],
        ["Length", f"{dims_original[0]:.2f} {unit_label}", f"{L:.2f}"],
        ["Width", f"{dims_original[1]:.2f} {unit_label}", f"{W:.2f}"],
        ["Height", f"{dims_original[2]:.2f} {unit_label}", f"{H:.2f}"],
    ]
    story.append(Paragraph("Inputs", styles["Heading2"]))
    story.append(_styled_table(inputs, col_widths=[160, 170, 170], has_header=True))
    story.append(Spacer(1, 10))

    summary = [
        ["Key Summary", "Value"],
        ["Total CO2 Required", f"{results['total_lb']:.2f} lb   ({results['total_kg']:.2f} kg)"],
        ["Total Cylinders", str(results["cylinders_total"])],
    ]
    story.append(Paragraph("Summary Highlights", styles["Heading2"]))
    story.append(_styled_table(summary, col_widths=[200, 300], has_header=True, accent_color=colors.HexColor("#1F4E79")))
    story.append(Spacer(1, 10))

    # Results
    out = [
        ["Metric", "Value"],
        ["Net Room Volume", f"{results['volume_m3']:.2f} m³   ({results['volume_ft3']:.2f} ft³)"],
        ["Base CO2 Required", f"{results['base_lb']:.2f} lb"],
        ["Total CO2 Required (with safety factor)", f"{results['total_lb']:.2f} lb   ({results['total_kg']:.2f} kg)"],
        ["Main Bank Cylinders", str(results["cylinders_main"])],
        ["Reserve Bank Cylinders", str(results["cylinders_reserve"])],
        ["Total Cylinders", str(results["cylinders_total"])],
    ]
    story.append(Paragraph("Calculation Results", styles["Heading2"]))
    story.append(_styled_table(out, col_widths=[240, 260], has_header=True))
    story.append(Spacer(1, 12))

    # Schematic (NEW style)
    story.append(Paragraph("Preliminary Piping Schematic (Conceptual)", styles["Heading2"]))
    story.append(Spacer(1, 6))
    drawing = build_isometric_schematic(system_data, results, width=520, height=330)
    story.append(DrawingFlowable(drawing))
    story.append(Spacer(1, 10))

    # Safety note
    safety = (
        "Safety Note: CO2 total flooding systems produce lethal concentrations. "
        "This report is conceptual/preliminary only. Confirm final design, safety interlocks, "
        "time delays, ventilation shutdown, lockout valves, and compliance with the applicable NFPA 12 edition "
        "and local AHJ requirements."
    )
    story.append(Paragraph(safety, styles["Normal"]))

    doc.build(story)


def _styled_table(data, col_widths=None, has_header=False, accent_color=colors.HexColor("#2F5597")):
    tbl = Table(data, colWidths=col_widths)
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ])
    if has_header:
        style.add("BACKGROUND", (0, 0), (-1, 0), accent_color)
        style.add("TEXTCOLOR", (0, 0), (-1, 0), colors.white)
        style.add("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
    tbl.setStyle(style)
    return tbl


# =============================
# GUI (CustomTkinter)
# =============================

class CO2App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CO₂ Total Flooding Calculator – NFPA 12 (Conceptual)")
        self.geometry("900x590")

        self.default_values = {
            "project_name": "Project A",
            "room_name": "CO2 Room",
            "length": "6",
            "width": "5",
            "height": "3",
            "safety_factor": "1.1",
            "cylinder_size": f"{CYLINDER_SIZE_LB:.0f}",
            "nozzle_tag": "E1-N1",
        }

        self.last_system_data = None
        self.last_results = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.input_frame = ctk.CTkFrame(self)
        self.output_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.output_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        self._build_inputs()
        self._build_outputs()

    def _build_inputs(self):
        f = self.input_frame
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="Project Inputs", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(10, 12), sticky="w", padx=12
        )

        _, self.project_name = self._add_entry(f, "Project Name", 1, "Project A")
        _, self.room_name = self._add_entry(f, "Room Name", 2, "CO2 Room")

        unit_labels = [label for label, _, _ in UNIT_OPTIONS]
        self.unit_label_var = ctk.StringVar(value=unit_labels[0])
        ctk.CTkLabel(f, text="Input Units").grid(row=3, column=0, sticky="w", padx=12, pady=(6, 2))
        self.unit_menu = ctk.CTkOptionMenu(
            f,
            values=unit_labels,
            variable=self.unit_label_var,
            command=lambda _: self._update_dimension_labels(),
        )
        self.unit_menu.grid(row=3, column=1, sticky="ew", padx=12, pady=(6, 2))

        self.len_label, self.len_m = self._add_entry(f, "Length (m)", 4, "6")
        self.wid_label, self.wid_m = self._add_entry(f, "Width (m)", 5, "5")
        self.hei_label, self.hei_m = self._add_entry(f, "Height (m)", 6, "3")

        ctk.CTkLabel(f, text="Hazard (NFPA 12 category)").grid(row=7, column=0, sticky="w", padx=12, pady=(10, 4))
        self.hazard = ctk.CTkOptionMenu(f, values=HAZARDS)
        self.hazard.set(HAZARDS[0])
        self.hazard.grid(row=7, column=1, sticky="ew", padx=12, pady=(10, 4))

        ctk.CTkLabel(f, text="Calculation Settings", font=ctk.CTkFont(weight="bold")).grid(
            row=8, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4)
        )
        _, self.safety_factor = self._add_entry(f, "Safety Factor", 9, "1.1")
        _, self.cylinder_size = self._add_entry(f, "Cylinder Size (lb)", 10, f"{CYLINDER_SIZE_LB:.0f}")

        # NEW: Include Reserve Bank
        ctk.CTkLabel(f, text="Cylinder Banks").grid(row=11, column=0, sticky="w", padx=12, pady=(12, 4))
        self.opt_reserve = ctk.CTkCheckBox(f, text="Include Reserve Bank (Total = Main + Reserve)", onvalue=True, offvalue=False)
        self.opt_reserve.select()  # default ON
        self.opt_reserve.grid(row=12, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 6))

        # NEW: Nozzle tag (for schematic)
        _, self.nozzle_tag = self._add_entry(f, "Nozzle Tag (schematic)", 13, "E1-N1")

        # Buttons
        self.calc_btn = ctk.CTkButton(f, text="Calculate", command=self.on_calculate)
        self.calc_btn.grid(row=14, column=0, padx=12, pady=(18, 10), sticky="ew")

        self.pdf_btn = ctk.CTkButton(f, text="Export PDF", command=self.on_export_pdf)
        self.pdf_btn.grid(row=14, column=1, padx=12, pady=(18, 10), sticky="ew")

        self.reset_btn = ctk.CTkButton(f, text="Reset Inputs", command=self._reset_inputs, fg_color="#6c757d")
        self.reset_btn.grid(row=15, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="ew")

        note = "Tip: You can adjust cylinder size to match the installed hardware."
        ctk.CTkLabel(f, text=note).grid(row=16, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))
        self._update_dimension_labels()

    def _build_outputs(self):
        f = self.output_frame
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="Results", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, pady=(10, 10), sticky="w", padx=12
        )

        self.results_box = ctk.CTkTextbox(f, wrap="word")
        self.results_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._set_results_text("Enter inputs, then click Calculate.")

    def on_calculate(self):
        try:
            system_data = self._collect_inputs()
            results = calculate_co2(system_data)

            self.last_system_data = system_data
            self.last_results = results

            self._set_results_text(self._format_results(system_data, results))

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_export_pdf(self):
        if not self.last_results or not self.last_system_data:
            messagebox.showwarning("Not calculated", "Please click Calculate first.")
            return

        default_name = f"{self.last_system_data.get('room_name','CO2_Room')}_CO2_Report.pdf".replace(" ", "_")
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=default_name,
        )
        if not path:
            return

        try:
            export_pdf(path, self.last_system_data, self.last_results)
            messagebox.showinfo("Success", f"PDF exported:\n{path}")
        except Exception as e:
            messagebox.showerror("PDF Export Error", str(e))

    def _collect_inputs(self) -> dict:
        project_name = self.project_name.get().strip()
        room_name = self.room_name.get().strip()

        unit_label = self.unit_label_var.get()
        unit = UNIT_LABEL_TO_UNIT.get(unit_label)
        if unit not in UNIT_TO_M:
            raise ValueError("Please select a valid unit.")

        L_input = self._read_float(self.len_m, "Length")
        W_input = self._read_float(self.wid_m, "Width")
        H_input = self._read_float(self.hei_m, "Height")
        factor = UNIT_TO_M[unit]
        L = L_input * factor
        W = W_input * factor
        H = H_input * factor

        hazard = self.hazard.get().strip()
        safety_factor = self._read_float(self.safety_factor, "Safety Factor")
        cylinder_size_lb = self._read_float(self.cylinder_size, "Cylinder Size (lb)")

        include_reserve = bool(self.opt_reserve.get())
        nozzle_tag = self.nozzle_tag.get().strip() or "E1-N1"

        return {
            "project_name": project_name,
            "room_name": room_name,
            "dimensions_m": (L, W, H),
            "dimensions_original": (L_input, W_input, H_input),
            "dimension_unit": unit,
            "dimension_unit_label": unit,
            "hazard": hazard,
            "safety_factor": safety_factor,
            "cylinder_size_lb": cylinder_size_lb,
            "include_reserve": include_reserve,
            "nozzle_tag": nozzle_tag,
        }

    def _format_results(self, system_data: dict, r: dict) -> str:
        reserve_txt = "Yes" if r.get("include_reserve", True) else "No"
        dims_original = system_data.get("dimensions_original", system_data.get("dimensions_m"))
        unit_label = system_data.get("dimension_unit_label", "m")
        return (
            f"Project: {system_data.get('project_name','')}\n"
            f"Room: {system_data.get('room_name','')}\n"
            f"Hazard: {system_data.get('hazard','')}\n"
            f"Cylinder Size: {r['cylinder_size_lb']:.0f} lb (~{r['cylinder_size_kg']:.1f} kg)\n"
            f"Reserve Bank Included: {reserve_txt}\n\n"
            f"Net Volume:\n"
            f"  - {r['volume_m3']:.2f} m³\n"
            f"  - {r['volume_ft3']:.2f} ft³\n\n"
            f"Dimensions ({unit_label}):\n"
            f"  - L: {dims_original[0]:.2f}, W: {dims_original[1]:.2f}, H: {dims_original[2]:.2f}\n\n"
            f"CO2 Requirement:\n"
            f"  - Base: {r['base_lb']:.2f} lb\n"
            f"  - Total (SF={system_data.get('safety_factor',1.1)}): {r['total_lb']:.2f} lb  ({r['total_kg']:.2f} kg)\n\n"
            f"Cylinders:\n"
            f"  - Main bank: {r['cylinders_main']}\n"
            f"  - Reserve bank: {r['cylinders_reserve']}\n"
            f"  - Total: {r['cylinders_total']}\n\n"
            f"Nozzle Tag (schematic): {system_data.get('nozzle_tag','E1-N1')}\n"
            f"Note: Schematic is preliminary/conceptual (not a shop drawing).\n"
        )

    def _add_entry(self, parent, label, row, default=""):
        label_widget = ctk.CTkLabel(parent, text=label)
        label_widget.grid(row=row, column=0, sticky="w", padx=12, pady=4)
        entry = ctk.CTkEntry(parent)
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky="ew", padx=12, pady=4)
        return label_widget, entry

    def _read_float(self, entry: ctk.CTkEntry, label: str) -> float:
        raw = entry.get().strip()
        if not raw:
            raise ValueError(f"{label} is required.")
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"{label} must be a number.") from exc

    def _update_dimension_labels(self):
        unit_label = self.unit_label_var.get()
        unit = UNIT_LABEL_TO_UNIT.get(unit_label, "m")
        label = unit if unit else "m"
        self.len_label.configure(text=f"Length ({label})")
        self.wid_label.configure(text=f"Width ({label})")
        self.hei_label.configure(text=f"Height ({label})")

    def _reset_inputs(self):
        self.project_name.delete(0, "end")
        self.project_name.insert(0, self.default_values["project_name"])
        self.room_name.delete(0, "end")
        self.room_name.insert(0, self.default_values["room_name"])
        self.unit_label_var.set([label for label, _, _ in UNIT_OPTIONS][0])
        self._update_dimension_labels()

        self.len_m.delete(0, "end")
        self.len_m.insert(0, self.default_values["length"])
        self.wid_m.delete(0, "end")
        self.wid_m.insert(0, self.default_values["width"])
        self.hei_m.delete(0, "end")
        self.hei_m.insert(0, self.default_values["height"])

        self.hazard.set(HAZARDS[0])
        self.safety_factor.delete(0, "end")
        self.safety_factor.insert(0, self.default_values["safety_factor"])
        self.cylinder_size.delete(0, "end")
        self.cylinder_size.insert(0, self.default_values["cylinder_size"])
        self.opt_reserve.select()
        self.nozzle_tag.delete(0, "end")
        self.nozzle_tag.insert(0, self.default_values["nozzle_tag"])
        self._set_results_text("Enter inputs, then click Calculate.")

    def _set_results_text(self, text: str):
        self.results_box.configure(state="normal")
        self.results_box.delete("1.0", "end")
        self.results_box.insert("1.0", text)
        self.results_box.configure(state="disabled")


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = CO2App()
    app.mainloop()


if __name__ == "__main__":
    main()
