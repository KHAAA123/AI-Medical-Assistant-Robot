# Setup day phan cung Arduino cho khay thuoc

Tai lieu nay bam theo sketch [`Khay.ino`](./Khay.ino). Arduino dieu khien:

- 1 dong co buoc xoay khay thuoc qua driver kieu `STEP/DIR`.
- 3 dong co DC dieu khien 3 cua bang module L298N.
- 6 cong tac hanh trinh, moi cua co 1 cong tac mo va 1 cong tac dong.

## 1. Bang chan Arduino

| Chuc nang | Chan Arduino | Dau noi phan cung |
| --- | --- | --- |
| Step khay | `D3` | `STEP` / `PUL` cua driver stepper |
| Direction khay | `D2` | `DIR` cua driver stepper |
| Enable khay | `D4` | `ENA-` cua TB6600 (`ENA+` noi `5V`) |
| Cua 1 IN1 | `D5` | L298N module 1 `IN1` |
| Cua 1 IN2 | `D6` | L298N module 1 `IN2` |
| Cua 2 IN1 | `D9` | L298N module 1 `IN3` |
| Cua 2 IN2 | `D10` | L298N module 1 `IN4` |
| Cua 3 IN1 | `D11` | L298N module 2 `IN1` |
| Cua 3 IN2 | `D12` | L298N module 2 `IN2` |
| Cong tac mo cua 1 | `A0` | 1 dau cong tac, dau con lai vao `GND` |
| Cong tac dong cua 1 | `A1` | 1 dau cong tac, dau con lai vao `GND` |
| Cong tac mo cua 2 | `A2` | 1 dau cong tac, dau con lai vao `GND` |
| Cong tac dong cua 2 | `A3` | 1 dau cong tac, dau con lai vao `GND` |
| Cong tac mo cua 3 | `A4` | 1 dau cong tac, dau con lai vao `GND` |
| Cong tac dong cua 3 | `A5` | 1 dau cong tac, dau con lai vao `GND` |

## 2. Dong co buoc xoay khay

Sketch hien tai khong dieu khien dong co buoc bang L298N. Can dung driver co chan `STEP` va `DIR`, vi du A4988, DRV8825 hoac TB6600.

Ket noi:

- Arduino `D3` -> driver `STEP` / `PUL`
- Arduino `D2` -> driver `DIR`
- Arduino `D4` -> driver `ENA-`; driver `ENA+` -> Arduino `5V`
- Arduino `GND` -> driver `GND`
- Nguon rieng cua motor -> nguon cong suat cua driver
- 2 cuon day cua motor buoc -> cac ngo ra motor cua driver

Trong sketch, `stepsPerRevolution = 1600`, nen cau hinh microstep tren driver de 1 vong quay tuong ung 1600 xung.

Khi reset, D4 dat driver vao trang thai tha motor de co the xoay khay cham bang tay.
Lenh `CALIBRATE:1` bat ENA va khoa khay; `TRAY:RELEASE` huy moc K1 va tha motor.
Neu module TB6600 co logic ENA nguoc, doi `STEPPER_ENABLE_ACTIVE_LEVEL` trong
`Cua_Khay.ino` sau khi thu khong tai. ENA chi tat ngo ra motor, khong cat nguon driver.

## 3. Module L298N cho cua 1 va cua 2

Dung module L298N thu nhat:

| Arduino | L298N module 1 | Thiet bi |
| --- | --- | --- |
| `D5` | `IN1` | Cua 1 |
| `D6` | `IN2` | Cua 1 |
| Motor cua 1 | `OUT1/OUT2` | Dong co cua 1 |
| `D9` | `IN3` | Cua 2 |
| `D10` | `IN4` | Cua 2 |
| Motor cua 2 | `OUT3/OUT4` | Dong co cua 2 |

Giu jumper `ENA` va `ENB` tren L298N, hoac noi `ENA/ENB` len 5V, vi sketch dang dieu toc bang PWM truc tiep tren cac chan `IN`.

## 4. Module L298N cho cua 3

Dung module L298N thu hai:

| Arduino | L298N module 2 | Thiet bi |
| --- | --- | --- |
| `D11` | `IN1` | Cua 3 |
| `D12` | `IN2` | Cua 3 |
| Motor cua 3 | `OUT1/OUT2` | Dong co cua 3 |

Luu y: tren Arduino Uno, `D12` khong phai chan PWM, nen chieu reverse cua motor 3 se chay theo muc digital bat/tat.

## 5. Cong tac hanh trinh

Sketch khai bao cac chan cong tac la `INPUT_PULLUP`, vi vay khong can dien tro keo ngoai. Moi cong tac dau nhu sau:

- Mot dau cong tac -> chan Arduino tuong ung `A0` den `A5`.
- Dau con lai -> `GND`.
- Nen dung cap chan `COM` va `NO` cua cong tac.

Trang thai dung voi sketch:

- Khong nhan cong tac: Arduino doc `HIGH`.
- Nhan cong tac: Arduino doc `LOW`.

Neu dung cong tac loai `NC`, logic se nguoc voi sketch va can sua code hoac doi cach dau day.

## 6. Nguon va GND chung

- Khong cap dong co tu chan 5V cua Arduino.
- Dung nguon rieng phu hop cho dong co DC va dong co buoc.
- Noi chung tat ca `GND`: Arduino, L298N module 1, L298N module 2 va driver stepper.
- Neu driver/module co chan 5V logic rieng, dau theo tai lieu cua module dang dung; khong dau nguon cong suat motor vao chan 5V cua Arduino.

## 7. Hanh vi khi khoi dong

Khi Arduino khoi dong, sketch tu dong goi `closeAllDoorsOnStartup()`:

- Cua 1 dong den khi cong tac `A1` bi nhan.
- Cua 2 dong den khi cong tac `A3` bi nhan.
- Cua 3 dong den khi cong tac `A5` bi nhan.
- Neu cua nao da dang nhan cong tac dong thi sketch bo qua cua do, khong kich motor.

Truoc khi cap nguon test, can lap dung 3 cong tac dong cua. Neu khong, motor co the chay den khi timeout 15 giay.

## 8. Lenh test qua Serial Monitor

Thiet lap Serial Monitor:

- Baud rate: `9600`
- Line ending: newline

Lenh test:

| Lenh | Tac dung | Phan hoi mong doi |
| --- | --- | --- |
| `PING` | Kiem tra ket noi | `DONE:PONG` |
| `STATUS` | Doc trang thai 3 cua va 6 CTHT | `STATUS:D1=...,D2=...,D3=...,A0=...` |
| `CALIBRATE:1` | Xac nhan co cau dang o K1 sau khi dat tay | `DONE:CALIBRATE` |
| `TRAY:RELEASE` | Huy moc K1 va tha motor de can chinh lai | `DONE:TRAY_RELEASE` |
| `HOME` | Dong tuan tu 3 cua ve CTHT dong | `DONE:HOME` |
| `TRAY:1` | Xoay khay den slot 1 | `DONE:TRAY` |
| `DOOR:1:OPEN` | Mo cua 1 | `DONE:DOOR` |
| `DOOR:1:CLOSE` | Dong cua 1 | `DONE:DOOR` |
| `DISPENSE:1:1` | Xoay slot 1 va mo cua 1 | `DONE:DISPENSE` |

Voi sketch `Cua_Khay.ino`, `STATUS` co them `T`, `TCAL` va `TBUSY`. Sau moi lan reset,
web phai gui `CALIBRATE:1` sau khi bac si da kiem tra co cau o K1; truoc do cac lenh
`TRAY` va `DISPENSE` se bi tu choi. `STATUS` tra them `TEN=0/1` de cho biet
driver dang tha hay dang giu khay.

Cac lenh test nhanh cu van duoc ho tro:

- `O1`, `C1`
- `O2`, `C2`
- `O3`, `C3`
- So `1` den `8` de xoay khay theo slot.

## 9. Xu ly neu chay nguoc hoac khong dung

- Neu cua chay nguoc huong: dao 2 day motor tren cap `OUT` cua cua do, hoac doi logic chan trong sketch.
- Neu motor dung vi timeout: kiem tra cong tac hanh trinh co keo chan ve `GND` khi cham khong.
- Neu khay xoay nguoc: dao logic `DIR`, doi day cuon motor theo tai lieu driver, hoac doi cach lap co khi.
- Neu Serial khong phan hoi: kiem tra dung port COM, baud `9600`, va cho Arduino reset xong sau khi mo port.

## 10. Ket noi voi webapp

Webapp doc port Arduino tu file `.env` truoc, vi du:

```text
ARDUINO_PORT=COM4
ARDUINO_TIMEOUT_MS=30000
```

Khi chay `python server.py`, backend se tu mo ket noi serial o nen. Neu Arduino reset khi mo COM, sketch se tu dua cua ve trang thai dong, nhung se bo qua nhung cua da dang nhan CTHT dong.

Trong giao dien bac si:

- Nut tung cua chi dieu khien dung cua do.
- Nut `Dong tat ca` gui lenh `HOME`.
- Trang thai cua lay tu lenh `STATUS`, khong con dua vao bien nho tren web.
