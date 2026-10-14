# KAIO: likely judge questions and honest answers

Short answers first. Details follow only if they ask.

**1. Is this a simulation or real?**
Real orbit (Φsat-2 TLE, SGP4), real NASA imagery and fire data for 20 days, real ground-station locations.
The spacecraft hardware (battery, thermal, computer, radio) is modelled. The decision code itself is real and
runs on a Raspberry Pi.

**2. How do you know an image's value onboard, without seeing the ground truth?**
Two cheap onboard numbers: thumbnail entropy (about 15 µs) and the land fraction of the footprint from a
stored land/water mask. A test proves the engine makes identical decisions when we scramble the hidden ground
truth, so it cannot be cheating.

**3. Why not just use entropy?**
On real data, clouds are the most textured scenes (64 % of all scenes). Raw entropy ranks worse than random:
27 % of the value in the top 30 %, against 30 % for random. Land mask × entropy reaches 79 %, against 82 % for
an oracle.

**4. Then why not use the land mask only?**
Good catch. In the nominal case the land mask alone is slightly better (87.1 vs 85.3), because there is enough
energy to process every land scene. Under stress, entropy matters: land-only drops to 78 (solar −30 %) and
66 (40 Wh battery), while E-LOTUS keeps 83 and 80.

**5. Is the Lyapunov method proven optimal here?**
No, and we don't claim it. Drift-plus-penalty has a textbook guarantee under stationary conditions; an orbit
isn't stationary. We use it as a principled scoring rule and verify everything empirically on 20 days, with
confidence intervals.

**6. Your gain over the rule engine is only about 4 points. Is that significant?**
Yes: 85.3 ± 0.6 against 81.5 ± 0.7. The intervals don't overlap, and E-LOTUS wins on 20 of 20 days. It also
completes 24 points more images and adapts without retuning; the rule engine collapses with a smaller
battery (2.9 %).

**7. Isn't the small-battery result a straw man?**
The rule engine was tuned for the nominal battery: process only above 50 % charge. With a 40 Wh battery, 50 %
equals the shutdown floor, so it keeps tripping it. That's exactly the weakness of fixed thresholds. E-LOTUS
uses the eclipse-survival floor computed from the orbit, so it adapts automatically.

**8. Where do you lose?**
With a 2.5× slower GPU (79.6 vs 80.6) and a 25 % weaker radiator (71.2 vs 79.8). In both cases the rule
engine runs above 45 °C for 37 % and 81 % of the day. If operators allow 60 °C for every job, E-LOTUS reaches
82.1 in the radiator case. It is an operator setting, not a limit of the method.

**9. What is the safety guard exactly?**
An independent check before any job starts. Using a linear energy budget and a first-order thermal model, it
predicts whether the job would leave the battery below the energy needed to survive the next eclipse, or end
above 45 °C. If so, the job is blocked and the reason is logged. Fire alerts may use the margin up to 60 °C.

**10. How would it get the pass schedule in real life?**
As today: ground operations compute passes days ahead and uplink the schedule. Eclipse times come from the
onboard orbit propagator. Our forecasts are perfect; real ones are very close.

**11. How much computing does it need?**
On the laptop, 0.16 ms per decision (median) and 0.002 % of one core over a day. On the Pi: [fill in from
`pi_benchmark.py`]. Only `numpy` and `sgp4`; no GPU and no training.

**12. What about the laser link to a neighbour? Your problem has one satellite.**
It's an optional extension. Without it E-LOTUS loses 1.6 points in the nominal case and still beats the rules.
It is modelled, not real.

**13. Why is the ceiling not 100 %?**
"% reachable" assumes every image goes down at its first pass, instantly and with unlimited resources. Real
processing and link time make that impossible, so 85 % is close to the physical limit.

**14. How did you avoid tuning on the test data?**
The engine weights (V and the debt weights) were chosen on a different workload seed (7), and the benchmark
uses seeds 2026+day. The safety rules (45 °C limit, alert exception) are design rules with no tuned number in
them, but we did look at their effect on a few benchmark days. The imagery days are shared. With more time,
we'd add fully held-out days with more NASA data.

**15. What would you do with more time?**
Hardware-in-the-loop on a flight-like computer, a small onboard cloud-mask network to replace the static land
prior, imperfect forecasts and sensor noise, and compare with a hindsight-optimal schedule.

**16. Who did what?**
Two prototypes merged into one. E-LOTUS brought the real-data world, the Lyapunov engine and the dashboard.
satsched brought the tested architecture, explanations, the drop rule, the bandwidth-aware baseline and the
statistical protocol.
