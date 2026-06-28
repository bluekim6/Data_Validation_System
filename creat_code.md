# 코드 작성 참조 정보

## Fasoo DRM 복호화 (`decrypt_fasoo.py`)
- 최근 next.js 프로젝트에서 사용한 방법은 **nextjs-fasoo-drm-decrypt.md**에 정리되어 있음. 필수 참조
- 운영 환경에서 업로드되는 CSV/Excel 파일에 **Fasoo DRM**이 걸려있을 수 있음
- 파일 업로드 처리 시 파싱 전에 `decrypt_fasoo.py`의 `decrypt_fasoo_file()` 함수를 호출하여 DRM 해제 후 진행
- Windows 환경 전용 (`C:/Windows/System32/f_nxldr.dll` 사용)
- DRM 해제 실패 시 원본 파일 경로를 그대로 반환 (파싱 시도는 계속)

```python
# 참조: decrypt_fasoo.py
from ctypes import CDLL

def decrypt_fasoo_file(uploaded_file_path):
    try:
        fasoo = CDLL("C:/Windows/System32/f_nxldr.dll")
        ret = fasoo.EnableDRM()
        if not ret:
            raise Exception("Fasoo 해제 실패")
    except Exception as e:
        print(f"DRM 해제 실패: {e}")
        return uploaded_file_path
    return uploaded_file_path
```

## Local LLM API 연결 (운영 사내 API & 개발 Gemini API 듀얼 연동)

개발 리소스 접근성을 위해 개발(Dev) 환경에서는 **Gemini API**를 사용하고, 운영 환경(폐쇄망)에서는 **사내 내부 API(sola_api)**를 사용하도록 설계한다.

| 항목 | 값 |
|---|---|
| 사내 API URL | `http://60.100.91.16:32029/TtoT-dev/` |
| 사내 API Key | `.env`의 `INTERNAL_API_KEY`로 관리 |
| Gemini Key | `.env`의 `GEMINI_API_KEY`로 관리 (`@google/genai` 패키지 사용) |
| 환경 설정 | `.env`의 `LLM_PROVIDER`로 구동 (값: `gemini` 또는 `internal`) |

### 호출 방식: `llmService.ts` 래퍼 사용
- `src/lib/llmService.ts`에 정의된 `callLLM(systemPrompt, userPrompt)` 함수를 Next.js API Route 내부에서 호출하여 사용한다.
- `LLM_PROVIDER` 환경 변수에 따라 알아서 분기 처리된다.

```typescript
// Next.js API Route 예시
import { callLLM } from '@/lib/llmService';

const systemPrompt = "너는 번역가이다.";
const userPrompt = "Hello, world!";
const answer = await callLLM(systemPrompt, userPrompt);
```

### 환경변수 (.env)
```env
INTERNAL_API_URL=http://60.100.91.16:32029/TtoT-dev/
INTERNAL_API_KEY=your_internal_api_key_here
DEFAULT_MODEL_NUMBER=9

LLM_PROVIDER=gemini        # 'gemini' (개발용) 또는 'internal' (운영 사내용)
GEMINI_API_KEY=your_gemini_key_here
```

### 사내 API 요청 파라미터 제약 준수
프롬프트를 래핑할 때, 사내 API 제약(messages는 **system + user 2개만** 지원)을 준수하도록 `callLLM(systemPrompt, userPrompt)` 시그니처 형태로 단일턴 기반 호출 방식을 고수한다. 대화 내역이 필요하면 `userPrompt`에 하나로 병합하여 넘긴다.

---

## 페이지·데이터 진입 속도 최적화 패턴 (필수 적용 — 2026-05-18 검증)

**배경**: file system을 데이터 저장소로 쓰는 Next.js 프로젝트에서 디렉토리·메타파일 수가 늘면 *그룹·문서 진입* 시 체감 지연이 누적된다. 본 프로젝트(document_copilot)에서 4가지 패턴 동시 적용 후 *"아이콘이 보이기 전에 화면이 전환된다"* 수준까지 가속됨. 새 Next.js 프로젝트 시작 시 처음부터 4개 패턴 모두 적용 권장.

### 1. 데이터 layer에 인메모리 TTL 캐시 (단일 process 전제, 가장 큰 효과)

`getX()` 같은 read 함수가 file system 또는 외부 API를 호출하면, 같은 process 안에서 짧은 TTL 캐시로 hit율을 극대화.

```ts
// src/lib/documentData.ts 예시
const TTL_MS = 30_000;
const cache = new Map<string, { value: T; expiresAt: number }>();

export async function getGroupDocuments(groupId: string): Promise<DocumentMeta[]> {
    const cached = cache.get(groupId);
    const now = Date.now();
    if (cached && cached.expiresAt > now) return cached.value;

    const value = await /* 실제 file system scan */;
    cache.set(groupId, { value, expiresAt: now + TTL_MS });
    return value;
}

// mutation 시 즉시 무효화
export function invalidateGroupDocuments(groupId: string): void {
    cache.delete(groupId);
}
```

**핵심 원칙**:
- TTL은 짧게(10~30초). mutation invalidate 누락에도 자동 복구.
- 모든 mutation 함수 안에서 invalidate 호출(`saveGroups`, `deleteDocument`, `upload` route 등).
- Next.js 단일 Node process가 모든 server component·API route에 공통이라 Map이 *자동 공유*된다.

### 2. file system 작업 병렬화 (Promise.all + fs.promises)

직렬 `fs.readFileSync` for-loop는 N개 파일에 비례해 O(N) waterfall이 된다. async + `Promise.all`로 동시 read.

```ts
import { promises as fsp } from 'fs';

// ❌ 느림 — 직렬
for (const folder of folders) {
    const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
}

// ✅ 빠름 — 병렬
const metas = await Promise.all(
    folders.map((folder) => readMetaSafe(path.join(...)))
);
```

**효과**: SSD에서 5~10배 빠름. HDD는 효과 적지만 손해는 없음.

**전염 처리 주의**: 함수가 async가 되면 모든 호출처에 `await` 추가 필요. server component(`async function Page`), API route, RAG orchestrator 등 도미노로 전파.

### 3. Next.js App Router의 `loading.tsx` 자동 활용

라우트별로 `loading.tsx`를 두면 페이지 전환 동안 자동으로 표시된다. 별도 state 관리 불필요.

```
src/app/loading.tsx              ← 기본 (모든 라우트 fallback)
src/app/group/[id]/loading.tsx   ← 그룹 페이지 진입 시
src/app/viewer/[docId]/loading.tsx ← viewer 진입 시
```

각 파일은 한 줄:
```tsx
import LoadingSpinner from "@/components/LoadingSpinner";
export default function Loading() { return <LoadingSpinner />; }
```

**효과**: 사용자가 클릭한 즉시 URL 바뀌고 spinner 표시 → 체감 즉시성 큼. 실제 데이터 fetch는 그 뒤에서 진행.

### 4. 로딩 컴포넌트는 *아이콘만*, 텍스트 라벨 제거

`"불러오는 중..."` 같은 텍스트는 추후 번역·메시지 관리·길이 변경 등 *부담만 큼*. 회전 아이콘 한 개로 사용자는 "처리 중"임을 충분히 인지한다.

```tsx
// src/components/LoadingSpinner.tsx 핵심
export default function LoadingSpinner({ overlay = true, size = "lg" }) {
    const spinner = (
        <div
            className={`${sizeMap[size]} border-purple-200 border-t-purple-600 rounded-full animate-spin`}
            role="status"
            aria-label="loading"  // 스크린리더만 읽음 (시각 표시 X)
        />
    );
    if (!overlay) return spinner;
    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-white/60 backdrop-blur-sm"
            style={{ cursor: "progress" }}   // 마우스 커서도 동시에 wait 모양
        >
            {spinner}
        </div>
    );
}
```

**원칙**:
- 시각 텍스트 라벨 X.
- 접근성용 `aria-label`만 영문 한 단어("loading") — 번역 불필요.
- `cursor: progress`로 마우스에도 즉시 피드백.

---

### 새 프로젝트 시작 시 적용 체크리스트

| 순서 | 작업 | 파일 |
|---|---|---|
| 1 | 데이터 layer에 TTL 캐시 + invalidate 함수 export | `src/lib/*Data.ts` |
| 2 | file system read를 `Promise.all` 병렬화 | 같은 파일 |
| 3 | mutation route(`upload`, `delete` 등)에서 invalidate 호출 | API route들 |
| 4 | 모든 라우트에 `loading.tsx` 1줄 추가 | `src/app/**/loading.tsx` |
| 5 | `LoadingSpinner` 공용 컴포넌트 — 텍스트 라벨 없이 아이콘만 | `src/components/LoadingSpinner.tsx` |
| 6 | 글로벌 CSS 또는 `cursor: progress`로 마우스 피드백 | spinner 안 |

**검증된 효과 (document_copilot, 2026-05-18)**:
- 그룹 페이지 첫 진입: 직렬 read → 병렬 read로 단축
- 같은 그룹 30초 안 재진입: 디스크 작업 0회 (cache hit)
- 사용자 체감: "아이콘 보이기 전에 화면 전환됨"

**주의 사항**:
- TTL 캐시는 *단일 process* 전제. multi-instance(serverless 등) 환경은 Redis 등 외부 캐시 필요.
- 캐시 무효화 누락은 TTL로 자동 복구되지만 사용자가 새 데이터를 즉시 못 볼 수 있음 → mutation 지점은 빠짐없이 invalidate 호출.
