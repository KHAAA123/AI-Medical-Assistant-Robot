# Chatbot Y Te Cho Jetson

Webapp tro ly y te thong minh chay bang Python backend + giao dien web tinh. App ho tro RAG du lieu Benh vien Hanh Phuc, hoi dap san pham Pharmacity, Gemini Live voice va dieu khien Arduino cho demo lay thuoc.

## Thanh phan chinh

- `server.py`: backend chinh, phuc vu UI va cac API `/robot/api/*`.
- `Web_emoji/`: giao dien web kiosk/touch-first.
- `RAG/`: engine tra cuu du lieu benh vien tu `hanhphuc.jsonl`.
- `pharmacity_chatbot/`: module tra cuu/summarize thong tin san pham Pharmacity.
- `Arduino/`: firmware Arduino va huong dan dau noi khay/cua.

## Cai dat tren Jetson

Yeu cau Python 3.10 tro len. Tren Jetson, kiem tra truoc:

```bash
python3 --version
```

Clone repo private tu GitHub, sau do cai dependencies:

```bash
git clone git@github.com:<your-user>/<your-private-repo>.git
cd <your-private-repo>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Tao file cau hinh local:

```bash
cp .env.example .env
nano .env
```

Gia tri can sua trong `.env`:

- `GEMINI_API_KEY`: API key Gemini.
- `ROBOT_APP_HOST`: mac dinh `127.0.0.1` cho kiosk. Khong dung `0.0.0.0` khi cac API dieu khien robot chua co xac thuc server-side.
- `ROBOT_APP_PORT`: mac dinh `8000`.
- `ARDUINO_PORT`: thuong la `/dev/ttyACM0` hoac `/dev/ttyUSB0` tren Jetson.

Neu Jetson khong co quyen mo cong serial, them user vao nhom `dialout`, dang xuat/dang nhap lai roi chay tiep:

```bash
sudo usermod -aG dialout "$USER"
```

Chay app:

```bash
python server.py
```

Mo trinh duyet tai:

```text
http://<jetson-ip>:8000
```

Neu chay truc tiep tren Jetson desktop, co the mo `http://127.0.0.1:8000`.

## Kiem tra

Chay test sau khi cai dependencies:

```bash
python -m unittest discover -v
```

Smoke check nhanh:

```bash
python -m RAG.rag_engine "Benh vien Hanh Phuc o dau?" --json
```

## Du lieu runtime

Thu muc `data/` duoc app tu tao khi can. Cac file nhu don thuoc upload, cau hinh Arduino va template Excel sinh ra luc chay khong duoc commit len GitHub de tranh day du lieu nhay cam.

File `.env` cung khong duoc commit. Hay dung `.env.example` lam mau cau hinh cho may moi.
