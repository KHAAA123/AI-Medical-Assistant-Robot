# Style Web App - Mobile Robot Y Te

File nay ghi nho phong cach giao dien hien tai cua du an, chu yeu tu `Web_new/index.html` va `Web_new/styles.css`. Khi them man hinh, sua component, hoac lam lai UI, uu tien giu dung tinh than nay.

## Tinh than thiet ke

- Giao dien la kiosk/web app cho robot y te: sach, than thien, ro rang, de cham tren man hinh cam ung.
- Cam giac tong the: hien dai, sang, mem, tin cay; khong qua nhieu decoration.
- Doi tuong su dung co the la benh nhan, bac si, nhan vien benh vien, nen thao tac phai lon, doc nhanh, it gay nham lan.
- Ngon ngu UI nen ngan gon, truc tiep, uu tien tieng Viet de hieu ngay.

## Bo mau chu dao

Dung he mau xanh ngoc - xanh duong nhe tren nen trang/sang.

```css
:root {
  --page-bg: #eaf5f6;
  --paper: #ffffff;
  --surface: #f6fbfb;
  --surface-strong: #e2f3f4;
  --ink: #102a34;
  --muted: #52707a;
  --line: #c7dde0;
  --accent: #0f9b9a;
  --accent-strong: #077a83;
  --accent-soft: #d9f4f2;
  --blue: #2177d1;
  --danger: #d92d20;
  --success: #098f61;
}
```

Nguyen tac:

- Nen trang/xanh rat nhat, khong dung nen toi.
- Mau chinh la teal `#0f9b9a`; trang thai chinh dung teal dam `#077a83`.
- Mau chu chinh gan den xanh `#102a34`, chu phu dung `#52707a`.
- Loi/canh bao dung do `#d92d20`, thanh cong dung xanh la `#098f61`.
- Co the dung xanh duong `#2177d1` cho chi tiet ban do, route, hoac thong tin phu.

## Nen va khung ung dung

- Toan bo app nam trong `.robot-frame` co ti le 16:9, giong man hinh gan tren robot.
- Khung ngoai co vien den xanh dam `#0c2c35`, bo goc rat lon, shadow sau.
- Nen trang co gradient xanh ngoc rat nhe va grid texture mo de tao cam giac cong nghe/y te.
- Tren man doc/mobile, bo vien khung va bo goc co the ve `0` de app full screen.

```css
.robot-frame {
  aspect-ratio: 16 / 9;
  border: clamp(10px, 1.2vw, 18px) solid #0c2c35;
  border-radius: clamp(34px, 3vw, 58px);
  background: var(--paper);
  box-shadow: 0 28px 70px rgba(21, 73, 83, 0.18);
}
```

## Typography

- Font chinh: `"Segoe UI", Tahoma, Arial, "Noto Sans", "Helvetica Neue", sans-serif`.
- Chu lon, dam, than thien voi man hinh cam ung.
- Heading chinh dung font-weight `800` den `850`, line-height chat `0.98` den `1.05`.
- Subtitle/body dung font-weight `600` den `750`, mau `--muted`.
- Eyebrow/label dung uppercase, font-weight `850` den `900`, mau `--accent-strong`.
- Tranh chu nho qua; UI nay uu tien khoang cach va do doc tu xa.

## Layout

- Dung CSS Grid la chinh.
- Man home co 3 vung: header thuong hieu + thoi gian, noi dung chinh + CTA, hang tac vu phu.
- Button/tile thuong co layout `icon + text`, icon nam trong o vuong bo goc.
- Cac man con dung `.screen-panel`: panel trang trong nhe, vien mong, shadow mem.
- Dung `clamp()` cho padding, gap, font-size, kich thuoc icon de scale theo man hinh kiosk.
- Mobile/portrait collapse ve 1 cot, app full viewport.

## Component DNA

### Nut chinh

- Nut chinh lon, nen gradient teal, chu trang, radius rat lon.
- Hover nang len nhe `translateY(-2px)` va tang shadow.
- Dung cho hanh dong quan trong nhat cua man hinh, vi du `Lay thuoc`.

```css
background: linear-gradient(135deg, var(--accent), var(--accent-strong) 62%, #045861);
border-radius: 42px;
box-shadow: 0 24px 48px rgba(7, 122, 131, 0.28);
```

### Tile tac vu

- Nen trang gan trong `rgba(255, 255, 255, 0.86-0.94)`.
- Vien `--line`, radius `30px`, shadow mem.
- Icon slot nen `--surface-strong`, bo goc `22px`.
- Text gom `strong` lon dam va `small` mo ta ngan.
- Dung cho cac tac vu: Dam thoai AI, Huong dan, Bac si, Map, Nhap ma, Quet QR.

### Panel/modal

- Panel noi tren nen man hinh, inset lon, padding lon.
- Nen trang trong nhe, vien mong, shadow mem.
- Nut dong la o vuong do nhat, icon Close, radius `22px`.
- Header trong panel gom label uppercase + heading lon.

### Form va settings

- Input/select cao, radius `20px`, nen xanh rat nhat.
- Focus dung vien teal va glow nhe.
- Settings chia thanh cac section card rieng, moi section co label uppercase va title dam.
- Action footer co nut phu trang/xam va nut chinh teal.

### Voice overlay

- Overlay full screen, nen gradient xanh ngoc/trang.
- Bot face lon, dang nhan dien cao, co animation nhe: breathing, blink, pupil movement, lip talk.
- Trang thai voice thay doi bang `data-state`: idle, listening, processing, speaking, error.
- Text voice status rat lon, transcript nho hon ben duoi.

## Phong cach emoji / bot face

Emoji trong app khong phai la emoji Unicode va cung khong phai icon phang. Day la mot mascot robot ve bang HTML/CSS, nam giua voice overlay, co mat, long may, ma hong, mieng va cac dau nhan cam xuc.

Tinh than can giu:

- De thuong nhung van sach va cong nghe, phu hop robot y te.
- Mat lon, bieu cam ro, tao cam giac dang lang nghe nguoi dung.
- Mau chinh cua emoji van theo he teal/cyan, co them hong nhe o ma de than thien.
- Khong bien bot thanh nhan vat hoat hinh qua tre con, khong dung style 3D nang, khong dung emoji vang mac dinh.
- Kich thuoc emoji rat lon, la trung tam cua man voice; UI phu khong duoc lan at bot face.

### Cau truc bot face

- `.voice-emoji`: container lon, aspect-ratio khoang `1.45`, co `drop-shadow` mem.
- `.bot-face`: khuon mat rong, trong suot, bo goc bat doi xung de tao dang dau robot.
- `.bot-eye`: hai mat tron lon, nen trang xanh rat nhat, co highlight trang va bong trong.
- `.bot-pupil`: con nguoi tron nhieu lop radial-gradient, tam den, vien teal/cyan phat sang.
- `.bot-brow`: long may la net cyan phat sang, hoi nghieng de tao cam xuc.
- `.bot-cheek`: ma hong radial-gradient, blur nhe, opacity cao vua phai.
- `.bot-mouth`: mieng co nen do hong dam, vien xam xanh, co animation khi noi.
- `.bot-expression-mark`: dau sao/cam xuc mau cyan hai ben mat, dung rat tiet che.

### Mau emoji

```css
/* Cyan/teal glow */
#47eee5;
#7df5f5;
#82f5f4;
#ccfffb;

/* Eye and neutral details */
#f9fcff;
#030812;
#6d8087;
#6e858e;

/* Cheek and mouth */
#ff7f9d;
#ff7894;
#642539;
#351823;
```

Nguyen tac mau:

- Mat va long may uu tien cyan/teal sang de hop voi mau thuong hieu.
- Ma hong chi la diem nhan cam xuc, khong duoc thanh mau chu dao.
- Mieng co mau hong/do dam de doc duoc khi bot dang noi.
- Glow phai mem, khong neon qua gat.

### Trang thai cam xuc

Dung `data-state` tren `.voice-overlay` va `data-expression` tren `.voice-emoji`.

- `idle`: bot vui/than thien, status "San sang nghe".
- `listening`: bot hoi tho nhe, mat sang hon, tao cam giac dang tap trung nghe.
- `processing`: bot nhich len/xuong nhe, mieng neutral, cam giac dang suy nghi.
- `speaking`: bot hoi tho nhe, ma hong sang hon, mieng co animation noi.
- `error`: long may doi huong, mieng buon, nhung van giu tone nhe nhang.

Khong nen them nhieu bieu cam moi neu khong can. Neu them, nen dua tren 3 truc: `happy`, `neutral`, `sad`.

### Animation emoji

Animation hien tai can giu nhe va cham:

- `voiceBreath`: scale nhe khoang `1 -> 1.035 -> 1`.
- `voiceThink`: dich len khoang `-8px` khi dang xu ly.
- `botNaturalLook`: con nguoi di chuyen nhe theo chu ky dai de bot co suc song.
- `botFocusLook`: tang brightness nhe khi listening/processing.
- `botBlink`: chop mat thinh thoang, chu ky khoang `7s`.
- `botCheekIdle` va `botCheekBloom`: ma hong thay doi opacity/blur nhe.
- `botLipTalk`: thay doi width/height cua mieng khi speaking.

Nguyen tac motion:

- Chuyen dong phai lam bot co cam giac song, khong gay roi mat.
- Khong dung animation nhanh lien tuc ngoai mieng khi speaking.
- Luon ton trong `prefers-reduced-motion: reduce`.

### Mau markup emoji

Neu can tao lai bot face, giu cau truc lop nhu sau:

```html
<div id="voiceEmoji" class="voice-emoji" data-expression="happy" aria-hidden="true">
  <div class="bot-face">
    <span class="bot-brow bot-brow-left"></span>
    <span class="bot-brow bot-brow-right"></span>
    <span class="bot-expression-mark bot-expression-mark-left"></span>
    <span class="bot-expression-mark bot-expression-mark-right"></span>
    <span class="bot-cheek bot-cheek-left"></span>
    <span class="bot-cheek bot-cheek-right"></span>
    <div class="bot-eye bot-eye-left">
      <span class="bot-pupil"></span>
    </div>
    <div class="bot-eye bot-eye-right">
      <span class="bot-pupil"></span>
    </div>
    <span class="bot-mouth"></span>
  </div>
</div>
```

### Dieu can tranh voi emoji

- Khong thay bang emoji vang mac dinh nhu 🙂, 🤖.
- Khong dung anh mascot raster neu khong bat buoc, vi CSS bot hien tai de animate theo state.
- Khong them qua nhieu chi tiet nho tren mat, vi kiosk can doc tu xa.
- Khong doi sang mat/sang tao vat the qua realistic; bot nen phang, mem, glow nhe.
- Khong lam bot nho thanh icon phu; trong voice overlay bot la nhan vat chinh.

## Icon va asset

- Uu tien icon PNG trong `Web_new/assets/Icon`.
- Icon dang dung: `QR.png`, `Mic.png`, `huong_dan.png`, `Doctor.png`, `Data.png`, `Close.png`, `Back.png`, `Done.png`, `Play.png`, `logo-3i.png`, `Khung.png`.
- Icon luon nam trong slot co aspect-ratio 1:1, `object-fit: contain`.
- Neu icon loi load, co fallback text hoac ky tu don gian.

## Radius va shadow

```css
--radius-xl: 42px;
--radius-lg: 30px;
--radius-md: 18px;
--shadow: 0 28px 70px rgba(21, 73, 83, 0.18);
--soft-shadow: 0 16px 36px rgba(20, 68, 78, 0.12);
```

Nguyen tac:

- Bo goc lon la mot phan nhan dien cua app.
- Shadow mem, mau xanh/xam, khong dung shadow den qua nang.
- Card nho dung `--soft-shadow`; khung app dung `--shadow`.

## Chuyen dong va tuong tac

- Chuyen dong ngan, mem: `160ms - 180ms ease`.
- Hover nang card/nut len `-2px`.
- Active keypad co the day xuong `1px`.
- Loading dung spinner teal 12 vach.
- Ho tro `prefers-reduced-motion: reduce`.

## Responsive

- Man ngang/kiosk: giu ti le 16:9, can giua viewport.
- Man doc/mobile: full viewport, khong vien ngoai, cac grid ve 1 cot.
- Settings grid tren man nho ve 1 cot, panel co scroll.
- Luon dung `minmax(0, 1fr)`, `clamp()`, `min()` de tranh tran text.

## Do and Don't

Nen:

- Dung teal/trang/xanh nhat lam he mau chinh.
- Tao nut lon, ro, de cham.
- Dung icon kem text cho hanh dong.
- Giu text ngan va truc tiep.
- Dung card/panel trang trong nhe voi shadow mem.
- Giu heading lon, dam, de doc tu xa.

Khong nen:

- Khong doi sang theme toi.
- Khong dung gradient tim/cam/den lam mau chinh.
- Khong them qua nhieu decoration ngoai grid va gradient nen nhe.
- Khong lam nut nho, text mong, kho cham.
- Khong pha bo khung kiosk 16:9 neu dang o Web_new.
- Khong dung radius nho/sac canh cho component chinh.

## Mau component moi

Khi them mot nut tac vu moi, uu tien cau truc nay:

```html
<button class="home-tool" type="button">
  <span class="icon-slot home-icon-slot">
    <img src="/robot/static/assets/Icon/YourIcon.png" alt="" data-optional-icon />
  </span>
  <span>
    <strong>Tieu de ngan</strong>
    <small>Mo ta mot dong</small>
  </span>
</button>
```

Khi them mot man con moi:

```html
<section class="screen" data-screen="new-screen">
  <div class="screen-panel">
    <button class="close-button" type="button" data-close aria-label="Dong">
      <img src="/robot/static/assets/Icon/Close.png" alt="" data-optional-icon />
      <span aria-hidden="true">x</span>
    </button>
    <header class="screen-header">
      <p>Nhom chuc nang</p>
      <h2>Tieu de man hinh</h2>
    </header>
  </div>
</section>
```

## Tom tat nhanh

Phong cach can nho: `medical kiosk`, `touch-first`, `teal soft UI`, `large bold Vietnamese typography`, `white translucent cards`, `rounded robot frame`, `icon + text action tiles`, `calm clinical technology`.
