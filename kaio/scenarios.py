"""Named benchmark scenarios: the nominal mission plus one stress case per scarce resource.

Each stress case is a round-number degradation of ONE resource, fixed before the benchmark is
run and applied without retuning any controller (same V, same thresholds).
"""

GS_SVALBARD = {"Svalbard (KSAT SvalSat)": (78.2297, 15.3975)}

SCENARIOS = {
    "nominal":            dict(label="Nominal", over={}),
    "energy_starved":     dict(label="Solar array -30 %", over=dict(p_face_w=14.0)),
    "battery_starved":    dict(label="Small battery (40 Wh) + solar -30 %", over=dict(battery_wh=40.0, p_face_w=14.0)),
    "storage_tight":      dict(label="Storage / 3 (2.7 GB)", over=dict(storage_mb=2700.0)),
    "compute_starved":    dict(label="GPU 2.5x slower", over=dict(gpu_gflops=400.0)),
    "downlink_starved":   dict(label="Downlink / 2, 20 deg mask", over=dict(downlink_mbps=5.0, elevation_mask_deg=20.0)),
    "event_surge":        dict(label="Fire season (3x alerts)", over=dict(fire_trigger_px=8)),
    "degraded_radiator":  dict(label="Radiator -25 %", over=dict(k_thermal=0.75)),
}
