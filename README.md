# doc-template

옵시디언 Markdown 한 파일을 기획·리서치 문서 HTML로 만듭니다. 라이트·다크, PC·모바일, 인쇄를 지원하고, 터미널·Claude Code·Codex·Claude 앱에서 같은 도구로 씁니다.

- 표지와 **띠지**(결론 한 줄 + 바뀌는 것·대가·뒤집힐 조건)로 첫 화면에서 결론이 읽힙니다.
- 본문 폭은 한글 한 줄 36자 안팎(36em), 행간 1.7입니다. 절 사이에는 타공 헤어라인이 들어갑니다.
- 색은 머리말 한 줄로 고릅니다. 다이칸야마 츠타야 서점이 소개한 책 표지에서 뽑은 여섯 배색, 흑백(검정·흰색 두 색만), 한 가지 색 모드가 있습니다.
- 정하지 않은 것은 본문에 이름표로 흩지 않고 **결정 모음** 한 곳에 모읍니다. 옵시디언 접이 상자(`> [!decide]- 질문`)로 쓰면 표지 아래 「정하지 않은 것 N가지 · 모아 보기」 줄과, 관련 절 머리의 「정할 것 N」 표시가 자동으로 붙습니다.
- 머리의 문서 번호와 메타의 상위 문서에 적은 티켓 번호(CCO-121 등)는 머리말 `jira:` 주소로 자동 링크됩니다.
- 구조 점검이 들어 있습니다. 결론을 맨 위에, 소제목은 결론 문장으로, 한 문서 한 독자 같은 원칙([가이드](src/doc_template/assets/guide.md))을 `review`가 점수와 고칠 점으로 알려 줍니다.

## 설치

[uv](https://docs.astral.sh/uv/)가 필요합니다. 없으면 먼저 설치합니다.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh     # 또는 brew install uv
uv tool install git+https://github.com/euna-source/doc-template
```

`doc-template`(터미널 명령)과 `doc-template-mcp`(MCP 서버) 두 명령이 생깁니다. 업데이트는 `uv tool upgrade doc-template` 한 줄입니다.

### Claude Code

```sh
claude mcp add doc-template -s user -- doc-template-mcp
```

### Codex

```sh
codex mcp add doc-template -- doc-template-mcp
```

### Claude 앱(데스크톱)

설정 → 개발자 → 설정 편집에서 `claude_desktop_config.json`에 아래를 넣고 앱을 다시 켭니다. `command`에는 `which doc-template-mcp`로 나온 전체 경로를 씁니다.

```json
{
  "mcpServers": {
    "doc-template": { "command": "/Users/<이름>/.local/bin/doc-template-mcp" }
  }
}
```

## 쓰는 법

AI에게는 이렇게 말하면 됩니다. "doc-template으로 이 내용을 기획 문서로 만들어 줘. 테마는 t1." MCP 도구 순서는 `get_guide` → `get_starter` → `review_document` → `render_document`입니다.

터미널에서는 이렇습니다.

```sh
doc-template starter plan -o 기획.md       # 시작 문서
doc-template render 기획.md                 # 기획.html 생성
doc-template render 기획.md --theme mono    # 흑백으로
doc-template review 기획.md                  # 구조 점검(점수·고칠 점)
doc-template guide                           # 구조 원칙
doc-template themes                          # 테마 목록
```

### 테마

| 테마 | 이름 | 출처 표지 |
|---|---|---|
| `t1` | 서가 전체 · 생성り × 노랑·주홍·초록 | 츠타야 서가 32권의 색 분포 |
| `t2` | 노랑 한 면 | 『する、しない。』 |
| `t3` | 흰 바탕 × 주홍 한 색 | 『世界』 junaida |
| `t4` | 회갈색 × 주홍 | 『信号旗K』 |
| `t5` | 연둣빛 풀색 | 『&Premium 京都』 |
| `t6` | 노랑·빨강·남색 | 『いろいろ色のはじまり』 |
| `paper` | 종이·먹 (v1 기본) | — |
| `mono` | 흑백 | 검정·흰색 두 색만. 위계는 크기·굵기·선·반전 |
| `one:#HEX` / `one:t3` | 한 가지 색 | 고른 색 하나를 절 번호·목차·형광펜·띠지에만 |

모든 테마는 라이트·다크 양쪽에서 글자 대비 4.5:1 이상을 검사합니다.

### Markdown 문법 (옵시디언 그대로)

| 쓰기 | 결과 |
|---|---|
| 머리말 `theme: t1`, `title`, `deck`, `status`, `meta`, `obi` | 표지·메타·띠지 |
| `## 이름 \| 소제목` | 번호가 붙은 절. 왼쪽은 목차 이름, 오른쪽은 큰 제목 |
| `==구절==` | 형광펜. 절마다 한 구절을 권합니다 |
| `> [!note]`, `> [!caution]`, `> [!unknown]` | 참고·주의·미확인 상자 |
| `- [ ] 할 일 @담당 ~기한`, `- [/]` 진행 중, `- [x]` 완료 | 다음 행동 목록 |
| 표, 첫 칸 `★ ` | 추천 행. 숫자 열이 있거나 다섯 열 이상이면 모바일에서 가로 스크롤, 아니면 카드 |
| `{{가안}}` | 이름표 |
| ```` ```stats ```` 줄마다 `값 \| 단위 \| 설명` | 요약 수치 |
| `[^1]` + `## 출처` 목록의 `{확인\|일부\|미확인}` | 각주와 출처 확인 상태 |
| `## 변경 이력` 표 | 이력 |

전체 예시는 `doc-template starter plan`과 `examples/sample-research.md`에 있습니다.

## 공개 배포(선택)

GitHub Pages가 켜진 저장소를 `DOC_TEMPLATE_PAGES_REPO=owner/repo`로 지정하면 `doc-template publish 기획.html 기획-slug`로 올리고 공개 URL을 받습니다. `gh` 로그인이 필요합니다. doc-template이 만든 HTML만 올라가고, 같은 저장소에 동시에 올리면 차례로 처리합니다. 회사 내부 문서는 공개 저장소에 올리지 마세요.

## 검사

```sh
uv run --with-editable . --with playwright python tests/verify_render.py   # 11테마 × 4폭 × 2모드
uv run --with-editable . python tests/test_safety.py                       # 주입·경로·덮어쓰기
uv run --with-editable . python tests/mcp_smoke.py                         # MCP 도구 호출
```
