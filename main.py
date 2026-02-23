import math
import tkinter as tk
from dataclasses import dataclass


@dataclass
class Charge:
    x: float
    y: float
    q: int


class FieldLineSimulator:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Electric Field Line Simulator")

        self.width = 1000
        self.height = 700
        self.charge_radius = 10
        self.softening_sq = 100.0

        self.charges: list[Charge] = []

        self.sign_var = tk.IntVar(value=1)
        self.magnitude_var = tk.IntVar(value=1)
        self.line_density_var = tk.IntVar(value=12)

        self._build_ui()
        self._redraw()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        controls = tk.Frame(container, padx=10, pady=10)
        controls.pack(side="left", fill="y")

        tk.Label(controls, text="Charge sign").pack(anchor="w")
        tk.Radiobutton(controls, text="Positive (+)", variable=self.sign_var, value=1).pack(anchor="w")
        tk.Radiobutton(controls, text="Negative (-)", variable=self.sign_var, value=-1).pack(anchor="w")

        tk.Label(controls, text="Charge magnitude (|q| in e)", pady=6).pack(anchor="w")
        tk.Spinbox(controls, from_=1, to=20, textvariable=self.magnitude_var, width=8).pack(anchor="w")

        tk.Label(controls, text="Lines per unit charge", pady=6).pack(anchor="w")
        density = tk.Scale(
            controls,
            from_=6,
            to=24,
            orient="horizontal",
            variable=self.line_density_var,
            length=170,
            command=lambda _: self._redraw(),
        )
        density.pack(anchor="w")

        tk.Button(controls, text="Undo Last", command=self._undo_last, width=16).pack(anchor="w", pady=(10, 4))
        tk.Button(controls, text="Clear All", command=self._clear_all, width=16).pack(anchor="w")

        instructions = (
            "Click in the canvas to add a charge.\n"
            "Field lines update automatically.\n\n"
            "Red = positive charge\n"
            "Blue = negative charge"
        )
        tk.Label(controls, text=instructions, justify="left", pady=14).pack(anchor="w")

        self.status = tk.Label(controls, text="Charges: 0")
        self.status.pack(anchor="w", pady=(8, 0))

        self.canvas = tk.Canvas(container, bg="white", width=self.width, height=self.height, highlightthickness=0)
        self.canvas.pack(side="right", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)

    def _on_click(self, event: tk.Event) -> None:
        x = float(event.x)
        y = float(event.y)

        if x < self.charge_radius or x > self.width - self.charge_radius:
            return
        if y < self.charge_radius or y > self.height - self.charge_radius:
            return

        q = self.sign_var.get() * self.magnitude_var.get()
        self.charges.append(Charge(x=x, y=y, q=q))
        self._redraw()

    def _undo_last(self) -> None:
        if self.charges:
            self.charges.pop()
            self._redraw()

    def _clear_all(self) -> None:
        self.charges.clear()
        self._redraw()

    def _field_at(self, x: float, y: float) -> tuple[float, float]:
        ex = 0.0
        ey = 0.0

        for c in self.charges:
            dx = x - c.x
            dy = y - c.y
            r2 = dx * dx + dy * dy + self.softening_sq
            inv_r3 = 1.0 / (r2 * math.sqrt(r2))
            ex += c.q * dx * inv_r3
            ey += c.q * dy * inv_r3

        return ex, ey

    def _find_hit_charge(
        self,
        x: float,
        y: float,
        target_sign: int,
        exclude: Charge | None = None,
        min_dist: float = 13.0,
    ) -> Charge | None:
        min_dist_sq = min_dist * min_dist
        for c in self.charges:
            if exclude is not None and c is exclude:
                continue
            if (c.q > 0) != (target_sign > 0):
                continue
            dx = x - c.x
            dy = y - c.y
            if dx * dx + dy * dy <= min_dist_sq:
                return c
        return None

    def _trace_line(self, source: Charge, x0: float, y0: float, direction: float) -> list[tuple[float, float]]:
        step = 3.0
        max_steps = 1800
        path: list[tuple[float, float]] = [(x0, y0)]
        target_sign = -1 if direction > 0 else 1

        x = x0
        y = y0

        for _ in range(max_steps):
            ex, ey = self._field_at(x, y)
            mag = math.hypot(ex, ey)
            if mag < 1e-8:
                break

            x += direction * step * ex / mag
            y += direction * step * ey / mag

            if x < 1 or x > self.width - 1 or y < 1 or y > self.height - 1:
                path.append((x, y))
                break

            if self._find_hit_charge(x, y, target_sign=target_sign, exclude=source) is not None:
                path.append((x, y))
                break

            path.append((x, y))

        return path

    def _seed_charges(self) -> list[tuple[Charge, float]]:
        positives = [c for c in self.charges if c.q > 0]
        negatives = [c for c in self.charges if c.q < 0]

        if positives:
            return [(c, 1.0) for c in positives]
        return [(c, -1.0) for c in negatives]

    def _draw_field_lines(self) -> None:
        if not self.charges:
            return

        sources = self._seed_charges()
        if not sources:
            return

        for c, direction in sources:
            seeds = max(8, abs(c.q) * self.line_density_var.get())
            start_radius = self.charge_radius + 6

            for i in range(seeds):
                angle = 2.0 * math.pi * i / seeds
                sx = c.x + start_radius * math.cos(angle)
                sy = c.y + start_radius * math.sin(angle)

                path = self._trace_line(c, sx, sy, direction)
                if len(path) < 2:
                    continue

                flat_points = [coord for pt in path for coord in pt]
                self.canvas.create_line(*flat_points, fill="#2f2f2f", width=1.0, smooth=True)

    def _draw_charges(self) -> None:
        for c in self.charges:
            color = "#d63b3b" if c.q > 0 else "#2f63d8"
            self.canvas.create_oval(
                c.x - self.charge_radius,
                c.y - self.charge_radius,
                c.x + self.charge_radius,
                c.y + self.charge_radius,
                fill=color,
                outline="black",
            )
            sign = "+" if c.q > 0 else "-"
            label = sign if abs(c.q) == 1 else f"{sign}{abs(c.q)}"
            self.canvas.create_text(c.x, c.y, text=label, fill="white", font=("Segoe UI", 9, "bold"))

    def _redraw(self) -> None:
        self.canvas.delete("all")
        self._draw_field_lines()
        self._draw_charges()
        self.status.config(text=f"Charges: {len(self.charges)}")


if __name__ == "__main__":
    app = tk.Tk()
    FieldLineSimulator(app)
    app.mainloop()
