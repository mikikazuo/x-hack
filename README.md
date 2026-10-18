# x-hack

X(旧Twitter)での自動いいね・情報収集Bot

---

## 起動方法

### 1. 個別アカウント（単一モード）で実行する場合
見たいアカウントだけを直接ターミナルから指定して起動できます。ログもそのアカウントのものだけが表示されます。

```bash
# 仮想環境をアクティベート、または .venv\Scripts\python を指定
python main.py --mode keiba
python main.py --mode goutraining-jp
python main.py --mode goutraining-eng
python main.py --mode rice
python main.py --mode anipath
```
※ `--mode`（または `-m`）を省略した場合はデフォルトの `keiba` が起動します。

#### 指定可能なモード一覧
| モード名（引数） | 説明 | 対象フォルダ / CSV |
| :--- | :--- | :--- |
| `keiba` | 競馬 | `keiba.csv` |
| `goutraining-jp` (または `fitness_jp`) | フィットネス（日本語版） | `goutraining-jp.csv` |
| `goutraining-eng` (または `fitness_en`) | フィットネス（英語版） | `goutraining-eng.csv` |
| `rice` | 米刻 | `rice.csv` |
| `anipath` | アニパス | `anipath.csv` |

---

### 2. 全アカウントを一括起動する場合（別ウィンドウ実行）
全アカウントを同時に動かしたい場合でも、**アカウントごとに独立したウィンドウ（個別画面）** が開き、ログが混ざらずに稼働します。

#### 方法 A: バッチファイルを実行（推奨・ダブルクリック可）
エクスプローラーから `run_all.bat` をダブルクリックするか、ターミナルで実行します。
```cmd
run_all.bat
```

#### 方法 B: PowerShellスクリプトを実行
```powershell
.\run_all.ps1
```

各ウィンドウのタイトルバーに `Bot [KEIBA]` のようにアカウント名が表示されます。特定のアカウントだけ停止したい場合は、そのウィンドウで `Ctrl + C` を押すかウィンドウを閉じるだけで安全に停止できます。
