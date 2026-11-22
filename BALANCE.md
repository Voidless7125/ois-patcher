# Objects in Space: how balanced are the modules?

A look at every module in `modules_*.txt` against the component data in `components.txt`. This is outside what the patcher
fixes (it only restores intent, it does not rebalance), so it is here, on `personal-variants`, as a base for a rebalance
plugin. Nothing in it changes the game. The tables are produced by `tools/balance/analyze.py`.

## Short answer

Not well balanced, but unevenly so. Two things are done well and one thing is not:

- **Components are priced sensibly.** Inside one module, the efficiency you can get from components (best config against
  worst) changes the price per unit of output by only about 18% for the median module (140 module/config sets, never more than 40%).
  Cheap components are the efficient ones but draw more power and emit more; the dear ones trade the other way. That is a real
  trade-off, not a trap.
- **Efficiency is a big lever.** A module's efficiency is `100 + the sum of its components' efficiency modifiers`, and the
  components differ a lot by configuration: the median module swings 17% between its worst and best configuration, and the
  extremes are RCSYS-2 (142 to 237%), KI-ORCHID (129 to 211%) and RCSYS-4 (133 to 201%).
- **The module base prices (`basevalue`) are where it goes wrong.** Within a class, price per unit of output differs
  between modules by 2.1x for the median class and by 9x for weapons, 4.7x for countermeasures, 4.5x for main drives, 3.8x
  for RCS and 3.5x for point defence. That is far larger than any component effect, and in four classes (countermeasures,
  point defence, solar, hackers) price does not rise with performance at all.

## How it was measured, and what to trust

| What | How | Confidence |
| :--- | :--- | :--- |
| Efficiency of a configuration | `100 + sum(efficiencymodifier)` of the installed components (`ComponentInterfaceInstance::getEfficiencyPercent`). The `asets`/`bsets` "step" values are 0 in every interface, so no other term applies. | Good. Read from the decompile; the results (110 to 237%) look like the efficiencies the game shows. Components are taken at full health. |
| Price | `basevalue + sum(component basecost)` (`ShipModule::getValue`) | Good for the module itself. I did not trace any shop mark-up or the sell price. |
| Output | the module's own stat, scaled by efficiency where the game does (thrust, jump range, rotation rate), otherwise taken as stated | Fair. Weapons use tubes / spin-up and ignore the ammunition. Sensors, comms and navigation have little to compare. |
| Power and emissions | compared as stated per module, not folded into price | A cheap module that burns more power is not wrong, so "dominated" below means worse on every listed stat |

Left out: the LADAR modules (the shop generator deliberately excludes them) and the NPC modules (`basevalue=0`).

## Findings by class

Grades are my judgement of how well price tracks performance.

| Class | Grade | Main findings |
| :--- | :--- | :--- |
| Jump drives | B+ | The best-priced class. Price per range varies only 1.4x. Still, DVJD-600 (3802, range 220, spin-up 21, power 16) beats DVJD-400 (4277, 160, 30, 20) and DVJD-500 on every nominal stat while costing less; KIJD-140S is beaten by KIJD-10 and KIJD-20 at the same price. |
| Generators | B | Price follows output well (correlation 0.85). MkIV makes 6 for the same 5904 that buys 4 from the MkVI. The Model One makes 3.5 for 5412 against MkIX's 4 for 4510, but it emits a third as much, which is a fair stealth trade. |
| Batteries | B- | Price tracks capacity (0.82). GG8 (20 capacity, 1800) is beaten by RS8 (39 for 1782); EB20 costs more than EB30 for less. |
| Sensors | B- | Priced by series, which roughly follows quality (0.71). The T0 and T9 sensors are the cheap, good ones; the Cosmos C1 costs the same as the C5 and M-series for lower quality or fewer ghosts. |
| Helm | C+ | Price tracks efficiency (0.89), though C-HLM1 and T-HLM4 are beaten by their siblings. The helm has no other stat to compare. |
| Main drives | C | GX_DELTA (thrust 1.1, base 2871) is worth about 2,300 per unit of thrust; GS-MDP (0.2, 2320) about 10,500. GX-ONE is beaten by GX-ASTRAL at the same price (thrust 0.6 vs 0.8, power 14 vs 10, emissions 170 vs 140) and KI-MDP by KI-BEHEMOTH, which is cheaper and better. The dearest drives (KI series, 3828) are not the strongest. |
| RCS | C- | RCSYS-KSM rotates at 50 for a base of 2505; RCSYS-KS rotates at 15 for 3036, about 4x worse value. |
| Comms | C | Nearly flat prices (1685, 2574, 2600) for sync times from 10 down to 5, so the price tier hardly matters. |
| Grapple arms | C | All four cost 2530 to 2783 with use times of 9 to 18 and no price link to either. |
| Hackers | C- | Price does not rise with performance (-0.20). DA-COMM does the same hack time as DAT-COMM for 1685 against 1498 with 45% more range, but LP9-2 costs the most and is beaten by LP9-100. |
| Solar | D+ | E SOLAR MK 2 makes 1.5 at the same 3344 where E SOLAR makes 2; SLSP AE makes 1 for the same 3648 as SLSP's 3. The four wings are the worst-priced of any class by correlation (-0.40). |
| Navigation | D | All twelve have the same plot time (10). The price (2088 to 3480) buys a screen skin, efficiency and power draw, nothing else. CNM/2 at 3480 has the lowest efficiency and highest power of the colour ones; NV/T1, T2 and T4 at 3190 are better in every way. |
| Point defence | D | Price falls as quality rises (-0.26). The PDL series is the dearest (4235) for the shortest range (5 to 7) and the slowest reload; PSL 10X (3150) has the same 1-in-5 hit chance as PDL 111 (4235) with range 16 against 6. SDS 55L is worth about a third of PDL 101 per unit of output. |
| Countermeasures | D | Price barely moves (2871 to 3190) for 2 to 10 tubes. PCM/9 is a 2-tube launcher at the same 3190 as CM/42's 6 tubes, and about 4.6 times worse value than SC/90. |
| Weapons | D | Five-fold difference in tubes at overlapping prices. MPL-010 (1 tube, base 2088) is worth roughly a tenth of SPL-9S (8 tubes, 2610). Ignoring power, 12 of the 16 launchers are beaten on price, tubes and spin-up by another one (for example every PL and PSP launcher by an SPL). This ignores the ammunition each launcher takes, which the module file does not say. |

## Efficiency: min and max by module

The efficiency columns in the table below come from the component lists of a module's five configurations
(`new`, `stealth`, `defence`, `lowpoweruse`, `boost`). Notes:

- `new` is what a freshly built copy has, and it is often not the best: KI-ORCHID's `new` is 129%, its worst, while its `boost`
  reaches 211%. A module sold in another configuration is the same price class with a very different output.
- Biggest swings (worst to best): RCSYS-2 142 to 237%, KI-ORCHID 129 to 211%, RCSYS-4 133 to 201%, KI-MDP 132 to 198%,
  RCSYS-KS 140 to 211%, PCM/9 139 to 200%.
- Smallest: solar wings (120 to 134%), D-H10 helm (131 to 140%), the navigation computers (124 to 170%). On these,
  efficiency barely matters.
- Higher efficiency costs components money, so `price per stat` moves only 1.0x to 1.4x across a module's configurations.

## If this were rebalanced

Not done, and only a starting point. The pattern that would fix most of it:

1. Make `basevalue` follow output within each class, using the better-priced classes (jump drives, generators, batteries) as the
   template, instead of using one price per series.
2. Take the dominated modules (list above) up or down in price, or give them a real niche (lower emissions, less power, more
   durable components).
3. Leave the component economy alone. It is the part that works.
4. Give navigation computers and helms a stat to buy (plot time, turning precision), or make their price flat and cheap.

## Per-module table

Price is base plus the cost of the `new` configuration's components. "Eff-adjusted stat" is the figure the "price per stat"
column divides into (units differ by class, so compare only inside a class; lower price per stat is better value).

| Class | Module | Base | Price (new) | Eff min / new / max | Eff-adjusted stat (new) | Price per stat (new) | across configs |
| :--- | :--- | ---: | ---: | :--- | ---: | ---: | :--- |
| arms | DRAK | 2783 | 3083 | 117 / 134 / 144 | 0.149 | 20,707 | 20,419 - 24,046 |
| arms | DRAK 2 | 2783 | 3113 | 118 / 140 / 150 | 0.117 | 26,683 | 26,683 - 31,791 |
| arms | GRA | 2530 | 2790 | 114 / 132 / 139 | 0.0825 | 33,818 | 33,818 - 40,931 |
| arms | GRA 5 | 2760 | 3100 | 110 / 142 / 151 | 0.0789 | 39,296 | 39,296 - 47,111 |
| batteries | T100 | 2400 | 2910 | 124 / 160 / 175 | 72 | 40.4 | 40.4 - 49.8 |
| batteries | R100 | 2160 | 2580 | 120 / 148 / 163 | 66.6 | 38.7 | 38.7 - 47.1 |
| batteries | X100 | 2160 | 2490 | 116 / 136 / 151 | 73.4 | 33.9 | 33.9 - 41 |
| batteries | EB10 | 2400 | 2600 | 114 / 124 / 130 | 71.9 | 36.2 | 36.2 - 43.8 |
| batteries | EB20 | 2904 | 3164 | 118 / 132 / 138 | 79.2 | 39.9 | 39.9 - 47.1 |
| batteries | EB30 | 2640 | 2900 | 118 / 132 / 140 | 87.1 | 33.3 | 33.3 - 40.1 |
| batteries | GG8 | 1800 | 2140 | 128 / 140 / 150 | 28 | 76.4 | 76.4 - 96.7 |
| batteries | GG10 | 1782 | 1882 | 116 / 116 / 162 | 34.8 | 54.1 | 50.7 - 62.4 |
| batteries | RS8 | 1782 | 2182 | 121 / 150 / 164 | 58.5 | 37.3 | 37.3 - 46.7 |
| cms | CML/2 | 2871 | 3651 | 133 / 152 / 154 | 0.57 | 6,405 | 6,405 - 7,323 |
| cms | CML/3 | 2871 | 3691 | 136 / 152 / 156 | 0.676 | 5,464 | 5,464 - 6,151 |
| cms | CM/42 | 3190 | 4030 | 138 / 156 / 159 | 0.936 | 4,306 | 4,306 - 4,866 |
| cms | PCM/9 | 3190 | 4400 | 138 / 178 / 200 | 0.445 | 9,888 | 9,692 - 11,096 |
| cms | PCM/9S | 3190 | 4420 | 142 / 180 / 185 | 0.8 | 5,525 | 5,525 - 6,119 |
| cms | PCM/9G | 3190 | 4460 | 148 / 186 / 192 | 1.12 | 3,996 | 3,996 - 4,435 |
| cms | SCM/4 | 2900 | 3700 | 142 / 152 / 154 | 1.52 | 2,434 | 2,434 - 2,792 |
| cms | SCM/2 | 2900 | 3640 | 138 / 144 / 146 | 1.15 | 3,160 | 3,160 - 3,608 |
| cms | SC/90 | 2900 | 3780 | 148 / 160 / 176 | 1.78 | 2,126 | 2,092 - 2,403 |
| comms | AE-35 | 1685 | 2175 | 137 / 138 / 144 | 0.138 | 15,761 | 15,761 - 20,723 |
| comms | AE-38 | 1685 | 2165 | 137 / 138 / 144 | 0.153 | 14,120 | 14,120 - 18,671 |
| comms | AR-20 | 1685 | 2205 | 141 / 142 / 148 | 0.158 | 13,975 | 13,975 - 18,384 |
| comms | MK-11 | 2574 | 3474 | 132 / 164 / 170 | 0.205 | 16,946 | 16,946 - 21,170 |
| comms | OL-08 | 2574 | 3554 | 137 / 172 / 180 | 0.215 | 16,530 | 16,471 - 20,289 |
| comms | MK-22 | 2574 | 3514 | 135 / 168 / 176 | 0.24 | 14,642 | 14,642 - 18,183 |
| comms | LP-02 | 2600 | 3120 | 132 / 140 / 144 | 0.233 | 13,371 | 13,360 - 16,294 |
| comms | LP-04 | 2600 | 3160 | 135 / 144 / 151 | 0.288 | 10,972 | 10,907 - 13,287 |
| comms | LP-S | 2600 | 3170 | 136 / 145 / 152 | 0.29 | 10,931 | 10,822 - 13,120 |
| generators | MkIV | 5904 | 6794 | 160 / 191 / 210 | 11.5 | 593 | 573 - 696 |
| generators | MkV | 5904 | 6814 | 162 / 193 / 206 | 9.65 | 706 | 695 - 828 |
| generators | MkVI | 5904 | 6774 | 162 / 189 / 208 | 7.56 | 896 | 864 - 1,035 |
| generators | MkVII | 4510 | 5150 | 161 / 161 / 200 | 4.83 | 1,066 | 953 - 1,068 |
| generators | MkVIII | 4510 | 5320 | 166 / 180 / 196 | 5.4 | 985 | 958 - 1,076 |
| generators | MkIX | 4510 | 5280 | 163 / 174 / 190 | 6.96 | 759 | 734 - 826 |
| generators | Model One | 5412 | 6142 | 161 / 172 / 186 | 6.02 | 1,020 | 990 - 1,106 |
| generators | MkVII | 5412 | 6122 | 160 / 170 / 184 | 6.8 | 900 | 877 - 984 |
| generators | MkVIII | 5412 | 6142 | 161 / 172 / 186 | 7.74 | 794 | 770 - 860 |
| hackers | LP9-2 | 2860 | 3740 | 131 / 164 / 170 | 16.4 | 228 | 228 - 283 |
| hackers | LP9-100 | 2574 | 3434 | 129 / 160 / 166 | 22.4 | 153 | 153 - 190 |
| hackers | OTH-S | 2317 | 3137 | 129 / 152 / 158 | 20.3 | 155 | 152 - 193 |
| hackers | OTH-3S | 2059 | 2899 | 131 / 156 / 162 | 17.7 | 164 | 164 - 211 |
| hackers | DA-COMM | 1685 | 2475 | 145 / 150 / 154 | 24 | 103 | 103 - 137 |
| hackers | DAT-COMM | 1498 | 2268 | 144 / 150 / 154 | 16.5 | 137 | 137 - 187 |
| helm | C-HLM1 | 3036 | 3876 | 132 / 158 / 174 | - | - | - |
| helm | C-H440 | 3036 | 3976 | 139 / 170 / 188 | - | - | - |
| helm | D-H10 | 1491 | 1921 | 131 / 131 / 140 | - | - | - |
| helm | D-H30 | 1863 | 2283 | 129 / 129 / 146 | - | - | - |
| helm | T-HLM4 | 2530 | 3070 | 132 / 144 / 156 | - | - | - |
| helm | T-HLM8 | 2277 | 2867 | 140 / 151 / 165 | - | - | - |
| jumpdrive | DVJD-400 | 4277 | 4807 | 148 / 172 / 175 | 275 | 17.5 | 17.5 - 20.1 |
| jumpdrive | DVJD-450 | 4277 | 4847 | 148 / 172 / 176 | 327 | 14.8 | 14.8 - 16.9 |
| jumpdrive | DVJD-500 | 4752 | 5362 | 149 / 172 / 177 | 344 | 15.6 | 15.6 - 17.6 |
| jumpdrive | DVJD-600 | 3802 | 4252 | 144 / 156 / 161 | 343 | 12.4 | 12.4 - 13.8 |
| jumpdrive | KIJD-10 | 5280 | 5770 | 140 / 164 / 164 | 426 | 13.5 | 13.5 - 15.5 |
| jumpdrive | KIJD-20 | 5280 | 5810 | 146 / 164 / 167 | 418 | 13.9 | 13.9 - 15.4 |
| jumpdrive | KIJD-140 | 5808 | 6378 | 147 / 172 / 174 | 404 | 15.8 | 15.8 - 18.2 |
| jumpdrive | KIJD-140R | 4752 | 5202 | 143 / 156 / 159 | 343 | 15.2 | 15.2 - 16.8 |
| jumpdrive | KIJD-140S | 5280 | 5770 | 144 / 164 / 164 | 344 | 16.8 | 16.8 - 18.9 |
| ladar | MKX-LADAR-A | 3480 | 4800 | 142 / 160 / 160 | 208 | 23.1 | 21.7 - 24.8 |
| ladar | MKX-LADAR-A-2 | 3828 | 5978 | 144 / 170 / 170 | 238 | 25.1 | 25 - 27.5 |
| ladar | MKX-LADAR-A-T | 3480 | 5210 | 146 / 174 / 174 | 261 | 20 | 20 - 24 |
| ladar | MTL-C100 | 3480 | 5230 | 130 / 176 / 176 | 238 | 22 | 22 - 27.3 |
| ladar | MTL-C150 | 3480 | 5240 | 132 / 177 / 177 | 257 | 20.4 | 20.4 - 25.2 |
| ladar | MTL-CC | 3480 | 5250 | 134 / 178 / 178 | 267 | 19.7 | 19.7 - 24.1 |
| ladar | TBL-B40 | 2900 | 4710 | 134 / 183 / 183 | 220 | 21.4 | 21.4 - 26.2 |
| ladar | TBL-B42 | 2900 | 4730 | 138 / 188 / 188 | 235 | 20.1 | 20.1 - 24.9 |
| ladar | TBL-B80 | 2900 | 4310 | 144 / 174 / 174 | 226 | 19.1 | 18.6 - 21.3 |
| maindrive | GX-ONE | 3190 | 4390 | 143 / 175 / 192 | 1.05 | 4,181 | 4,181 - 4,822 |
| maindrive | GX_DELTA | 2871 | 3871 | 129 / 151 / 164 | 1.66 | 2,331 | 2,328 - 2,700 |
| maindrive | GX-ASTRAL | 3190 | 4390 | 150 / 175 / 192 | 1.4 | 3,136 | 3,136 - 3,804 |
| maindrive | GS-MDP | 2320 | 3430 | 143 / 163 / 177 | 0.326 | 10,521 | 10,521 - 12,597 |
| maindrive | GS-MDP-2 | 2320 | 3390 | 137 / 158 / 171 | 0.632 | 5,364 | 5,364 - 6,441 |
| maindrive | GS-APOLLO | 2552 | 3982 | 142 / 164 / 178 | 0.656 | 6,070 | 6,070 - 7,216 |
| maindrive | KI-ORCHID | 3828 | 4358 | 129 / 129 / 211 | 0.516 | 8,446 | 7,460 - 8,768 |
| maindrive | KI-MDP | 3828 | 5358 | 132 / 179 / 198 | 0.895 | 5,987 | 5,889 - 7,014 |
| maindrive | KI-BEHEMOTH | 3445 | 5771 | 134 / 184 / 197 | 1.11 | 5,220 | 4,316 - 5,305 |
| navcom | CNM/1 | 3480 | 3920 | 131 / 131 / 135 | - | - | - |
| navcom | CNM/2 | 3480 | 3920 | 124 / 132 / 138 | - | - | - |
| navcom | CNM/R | 3190 | 3770 | 133 / 148 / 158 | - | - | - |
| navcom | NM/60 | 2088 | 2588 | 138 / 138 / 146 | - | - | - |
| navcom | NM/80 | 2088 | 2618 | 142 / 142 / 151 | - | - | - |
| navcom | NM/99 | 2610 | 3180 | 142 / 146 / 156 | - | - | - |
| navcom | SNM/40 | 2784 | 3324 | 143 / 143 / 152 | - | - | - |
| navcom | SNM/50 | 3480 | 4020 | 143 / 143 / 152 | - | - | - |
| navcom | SNM/66 | 3480 | 4000 | 140 / 140 / 170 | - | - | - |
| navcom | NV/T1 | 3190 | 4210 | 144 / 178 / 192 | - | - | - |
| navcom | NV/T2 | 3190 | 4130 | 138 / 168 / 182 | - | - | - |
| navcom | NV/T4 | 3190 | 4090 | 136 / 166 / 180 | - | - | - |
| pds | PDL 101 | 4235 | 4855 | 137 / 150 / 154 | 0.0625 | 77,680 | 77,680 - 84,764 |
| pds | PDL 111 | 4235 | 4855 | 137 / 150 / 154 | 0.075 | 64,733 | 64,733 - 70,636 |
| pds | PDL 400 | 4235 | 4835 | 136 / 150 / 154 | 0.075 | 64,467 | 64,467 - 71,805 |
| pds | MPD 100 | 3850 | 4360 | 130 / 140 / 142 | 0.1 | 43,600 | 43,600 - 48,953 |
| pds | MPD 200 | 3465 | 3955 | 129 / 136 / 139 | 0.0777 | 50,892 | 50,892 - 56,971 |
| pds | MPD 250 | 3080 | 3490 | 124 / 128 / 131 | 0.0731 | 47,715 | 47,715 - 54,287 |
| pds | PSL 900 | 3850 | 4660 | 133 / 154 / 156 | 0.128 | 36,312 | 36,312 - 40,212 |
| pds | PSL 940 | 3465 | 4245 | 129 / 150 / 152 | 0.1 | 42,450 | 42,450 - 47,361 |
| pds | PSL 10X | 3150 | 3980 | 136 / 156 / 159 | 0.104 | 38,269 | 38,269 - 43,106 |
| pds | SDS 080 | 3150 | 3950 | 133 / 154 / 156 | 0.171 | 23,084 | 23,084 - 26,224 |
| pds | SDS 090 | 3150 | 3970 | 134 / 154 / 157 | 0.128 | 30,935 | 30,935 - 34,884 |
| pds | SDS 55L | 3850 | 4770 | 138 / 166 / 166 | 0.213 | 22,413 | 22,413 - 25,004 |
| rcs | RCSYS-2 | 3340 | 6070 | 142 / 212 / 237 | 74.2 | 81.8 | 81.3 - 92.8 |
| rcs | RCSYS-4 | 3036 | 4596 | 132 / 182 / 201 | 54.6 | 84.2 | 84.2 - 96.9 |
| rcs | RCSYS-KS | 3036 | 4966 | 140 / 190 / 211 | 28.5 | 174 | 174 - 203 |
| rcs | RCSYS-KSM | 2505 | 3955 | 130 / 172 / 192 | 86 | 46 | 46 - 54.3 |
| rcs | RCSYS-GSS | 2226 | 3156 | 140 / 140 / 209 | 35 | 90.2 | 90.2 - 118 |
| rcs | RCSYS-G9 | 2024 | 3754 | 142 / 164 / 179 | 26.2 | 143 | 143 - 170 |
| rcs | RCSYS-G9S | 1619 | 2549 | 140 / 140 / 149 | 16.8 | 152 | 152 - 189 |
| sensors | C1-SNS | 3432 | 4022 | 135 / 150 / 158 | 1.2 | 3,352 | 3,305 - 3,896 |
| sensors | C5-SNS | 3432 | 4042 | 136 / 152 / 160 | 1.82 | 2,216 | 2,193 - 2,591 |
| sensors | D2-SNS | 1685 | 2285 | 148 / 152 / 160 | 0.608 | 3,758 | 3,758 - 4,866 |
| sensors | D4-SNS | 1872 | 2422 | 145 / 145 / 152 | 0.87 | 2,784 | 2,784 - 3,472 |
| sensors | M1-SNS | 3432 | 4022 | 135 / 150 / 158 | 1.35 | 2,979 | 2,938 - 3,463 |
| sensors | M2-SNS | 3432 | 4042 | 136 / 150 / 158 | 1.5 | 2,695 | 2,647 - 3,109 |
| sensors | SL-SNS | 3120 | 3680 | 138 / 145 / 151 | 1.45 | 2,538 | 2,523 - 3,004 |
| sensors | SM-SNS | 3120 | 3690 | 139 / 146 / 152 | 1.61 | 2,298 | 2,276 - 2,697 |
| sensors | SQ-SNS | 3120 | 3700 | 140 / 147 / 153 | 1.91 | 1,936 | 1,922 - 2,279 |
| sensors | T9-SNS | 2860 | 3460 | 133 / 149 / 156 | 0.894 | 3,870 | 3,840 - 4,594 |
| sensors | T0-SNS | 2860 | 3510 | 140 / 155 / 163 | 1.24 | 2,831 | 2,814 - 3,357 |
| solar | SLSP | 3648 | 3828 | 120 / 120 / 126 | 3 | 1,276 | 1,276 - 1,459 |
| solar | SLSP AE | 3648 | 3848 | 124 / 124 / 130 | 1 | 3,848 | 3,848 - 4,448 |
| solar | E SOLAR | 3344 | 3544 | 124 / 124 / 130 | 2 | 1,772 | 1,772 - 2,072 |
| solar | E SOLAR MK 2 | 3344 | 3564 | 127 / 128 / 134 | 1.5 | 2,376 | 2,376 - 2,811 |
| weapons | PL-900 | 2871 | 3651 | 138 / 152 / 154 | 0.253 | 14,412 | 14,412 - 16,478 |
| weapons | PL-910 | 2871 | 3651 | 133 / 152 / 154 | 0.283 | 12,911 | 12,911 - 14,761 |
| weapons | PL-920 | 2871 | 3751 | 140 / 164 / 167 | 0.305 | 12,294 | 12,294 - 14,055 |
| weapons | PL-940 | 3190 | 4050 | 142 / 160 / 162 | 0.333 | 12,150 | 12,150 - 13,700 |
| weapons | MPL-010 | 2088 | 2528 | 133 / 134 / 139 | 0.0506 | 49,994 | 49,994 - 61,067 |
| weapons | MPL-040 | 1856 | 2276 | 131 / 132 / 137 | 0.0943 | 24,139 | 24,139 - 29,922 |
| weapons | MPL-060 | 1856 | 2206 | 121 / 124 / 127 | 0.0936 | 23,572 | 23,572 - 29,367 |
| weapons | MPL-100 | 1856 | 2256 | 128 / 129 / 132 | 0.149 | 15,157 | 15,157 - 18,704 |
| weapons | PSP-440 | 2610 | 3050 | 133 / 134 / 139 | 0.312 | 9,787 | 9,787 - 10,249 |
| weapons | PSP-450 | 2610 | 3070 | 134 / 134 / 139 | 0.353 | 8,706 | 8,706 - 10,189 |
| weapons | PSP-460 | 2610 | 3100 | 133 / 138 / 140 | 0.363 | 8,536 | 8,536 - 10,014 |
| weapons | PSP-5X | 2610 | 3110 | 134 / 139 / 142 | 0.388 | 8,017 | 8,017 - 9,322 |
| weapons | SPL-5S | 2610 | 3100 | 133 / 138 / 140 | 0.487 | 6,365 | 6,365 - 7,467 |
| weapons | SPL-6S | 2610 | 3140 | 136 / 142 / 145 | 0.552 | 5,686 | 5,686 - 6,635 |
| weapons | SPL-7 | 2900 | 3480 | 141 / 146 / 157 | 0.538 | 6,470 | 6,417 - 7,404 |
| weapons | SPL-9S | 2610 | 3170 | 140 / 146 / 149 | 0.584 | 5,428 | 5,428 - 6,349 |
