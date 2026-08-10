# Parity with Understand

How close OpenUnderstand's output is to SciTools Understand's on the
same source. Generated from the comparison harness output; the harness needs
a licensed Understand install, so it lives outside this repository.

Both tools analyse the same fixture. Entities are matched on
(kind family, normalised long name); references on (kind, entity,
scope, file, line, column).

## JSON

| | Understand | OpenUnderstand |
| --- | ---: | ---: |
| Entities | 1236 | 2095 |

- Entities matched: **1235** of 1236
- Entities with no Understand counterpart: 860
- Open findings: 72

### Entities by kind family

| Family | Understand | OpenUnderstand | Δ |
| --- | ---: | ---: | ---: |
| parameter | 452 | 452 | +0 |
| variable | 418 | 878 | +460 |
| method | 292 | 508 | +216 |
| constructor | 38 | 38 | +0 |
| class | 22 | 182 | +160 |
| unknown | 8 | 8 | +0 |
| package | 2 | 2 | +0 |
| interface | 2 | 2 | +0 |
| annotation | 2 | 2 | +0 |
| file | 0 | 22 | +22 |
| module | 0 | 1 | +1 |

### Largest reference gaps

| Kind | Understand | OpenUnderstand | Missing |
| --- | ---: | ---: | ---: |
| `Java Use` | 1683 | 903 | +780 |
| `Java Useby` | 1683 | 903 | +780 |
| `Java Throw` | 141 | 0 | +141 |
| `Java Throwby` | 141 | 0 | +141 |
| `Java DotRef` | 102 | 0 | +102 |
| `Java DotRefby` | 102 | 0 | +102 |
| `Java Couple` | 63 | 0 | +63 |
| `Java Coupleby` | 63 | 0 | +63 |
| `Java Modifyby` | 48 | 0 | +48 |
| `Java Modify` | 48 | 0 | +48 |

### Open findings

| Score | Severity | Finding |
| ---: | --- | --- |
| 16.3 | wrong-data | 323 duplicate entity rows across 189 logical entities |
| 16.1 | wrong-data | 860 of 2095 OpenUnderstand entities have no Understand counterpart |
| 12.6 | missing-data | 6736 references Understand finds are absent, ignoring position (recall 50%) |
| 11.9 | wrong-data | 68 references written as 'Java Importby', which Understand never emits here |
| 11.9 | wrong-data | 68 references written as 'Java Import', which Understand never emits here |
| 11.9 | wrong-data | 68 references match only once ent and scope are swapped |
| 11.7 | wrong-data | CountOutput disagrees with Understand on 215 of 220 entities (2% agreement) |
| 11.5 | wrong-data | CountInput disagrees with Understand on 198 of 220 entities (10% agreement) |
| 10.8 | wrong-data | MaxNesting disagrees with Understand on 142 of 247 entities (43% agreement) |
| 10.5 | wrong-data | CountLineCodeExe disagrees with Understand on 126 of 246 entities (49% agreement) |
| 10.4 | wrong-data | api.py changes the parameter entity count by -121 even though the database matches Understand |
| 9.8 | wrong-data | 31 references written as 'Java Use Annotation', which Understand never emits here |

## calculator_app

| | Understand | OpenUnderstand |
| --- | ---: | ---: |
| Entities | 72 | 143 |

- Entities matched: **72** of 72
- Entities with no Understand counterpart: 71
- Open findings: 57

### Entities by kind family

| Family | Understand | OpenUnderstand | Δ |
| --- | ---: | ---: | ---: |
| parameter | 26 | 26 | +0 |
| method | 17 | 29 | +12 |
| variable | 15 | 47 | +32 |
| class | 8 | 23 | +15 |
| package | 6 | 6 | +0 |
| file | 0 | 8 | +8 |
| module | 0 | 4 | +4 |

### Largest reference gaps

| Kind | Understand | OpenUnderstand | Missing |
| --- | ---: | ---: | ---: |
| `Java Containin` | 8 | 0 | +8 |
| `Java Contain` | 8 | 0 | +8 |
| `Java Couple` | 7 | 0 | +7 |
| `Java Coupleby` | 7 | 0 | +7 |
| `Java Modifyby` | 5 | 0 | +5 |
| `Java Modify` | 5 | 0 | +5 |
| `Java Use Return` | 4 | 1 | +3 |
| `Java DotRef` | 3 | 0 | +3 |
| `Java Useby Return` | 4 | 1 | +3 |
| `Java DotRefby` | 3 | 0 | +3 |

### Open findings

| Score | Severity | Finding |
| ---: | --- | --- |
| 10.2 | wrong-data | 71 of 143 OpenUnderstand entities have no Understand counterpart |
| 7.6 | wrong-data | 14 duplicate entity rows across 14 logical entities |
| 7.4 | missing-data | 178 references Understand finds are absent, ignoring position (recall 65%) |
| 7.2 | wrong-data | 12 references written as 'Java Importby', which Understand never emits here |
| 7.2 | wrong-data | 12 references written as 'Java Import', which Understand never emits here |
| 6.8 | wrong-data | 10 references match only once ent and scope are swapped |
| 6.5 | wrong-data | 9 references written as 'Java ModuleUseby', which Understand never emits here |
| 6.5 | wrong-data | 9 references written as 'Java ModuleUse', which Understand never emits here |
| 6.5 | wrong-data | 14 references have the right line but the wrong column (312 of 326 match once the column is included) |
| 6.2 | wrong-data | 8 references written as 'Java Openby', which Understand never emits here |
| 6.2 | wrong-data | 8 references written as 'Java Open', which Understand never emits here |
| 5.4 | wrong-data | CountInput disagrees with Understand on 11 of 14 entities (21% agreement) |
