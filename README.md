# laity_shorts

## 현재 상태와 공유 방식

신사모 릴스는 **수동 병합·배포 후 공개 예정**입니다. 기존 세 편과 신사모 릴스는 모두 `published: true`로 설정되어 있으며 날짜에 따른 자동 공개는 없습니다.

- `/`: `media.json`에서 공개한 영상만 기존 순서대로 표시. 여러 편이면 세로 스크롤·스와이프.
- `/?reel=responsibility`, `/?reel=essence`, `/?reel=prayer`, `/?reel=sinsamo`: 해당 영상 **한 편만** 표시. 다른 영상의 제목·포스터·재생 주소·이동 링크 없음.
- 미공개 영상의 개별 링크: “아직 공개되지 않은 영상입니다.”만 표시.
- 잘못된 reel 값: 기본 화면. 공개 영상이 없으면 “공개된 영상이 아직 없습니다.” 표시.

| 한국시간 발송 계획 | reel_id | 영상·원본 보관 경로 | 저장소 공개 설정 |
| --- | --- | --- | --- |
| 2026. 11. 17. | responsibility | 권한과 책임 / public/videos/responsibility.mp4 | true |
| 2026. 11. 19. | essence | 목적헌금의 본질 / public/videos/offering.mp4 | true |
| 2026. 11. 21. | prayer | 예배·기도·사역 참여 / public/videos/example.mp4 | true |
| 2026. 11. 25. | sinsamo | 우리 교회에 무슨 일이 일어나고 있을까요? / public/videos/sinsamo.mp4 | true |

신사모 릴스 발송 전에는 병합·배포 후 [전용 링크](https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=sinsamo)를 열어 실제 재생을 확인하세요.

## 공개 상태 변경과 다음 영상 발송

단일 설정 `media.json`에서 `reel_id`, `label`, `video`, `poster`, `published`, `send_date` 및 파일 식별 정보를 관리합니다. 날짜는 발송 계획일 뿐 자동 공개 기능이 아닙니다. `published`를 생략하면 미공개입니다.

1. 19일·21일에 순차 공개하려면 해당 영상의 `published`를 `true`로 변경합니다. 다른 영상 상태는 의도한 대로 유지합니다.
2. `python3 scripts/build.py`와 테스트·Docker 검사를 실행합니다.
3. 별도 브랜치에서 커밋하고 PR을 만듭니다.
4. 사용자가 수동 검토·병합하고 Cloudtype에서 기존 방식으로 배포합니다. 파일 수정이나 날짜 도달만으로 운영 사이트가 바뀌지 않습니다.
5. 배포된 개별 링크·영상·포스터·Range 응답을 확인한 뒤 문자를 보냅니다.

개별 링크와 문자 예시는 [docs/SHARING.md](docs/SHARING.md)를 참고하세요.

## 로컬 실행과 검사

Docker와 Python 3이 필요합니다. Nginx가 정적 HTML·MP4를 제공하며 DB·API 서버는 없습니다.

    python3 scripts/build.py
    docker build -t laity-shorts .
    docker run --rm -p 8080:8080 laity-shorts

브라우저에서 http://localhost:8080 으로 접속합니다. `public/`는 원본 보관 디렉터리이므로 파일 서버로 직접 제공하지 마세요. 배포는 필터링된 `dist/site`만 사용합니다. 쿼리 라우팅과 HTTP Range 검사는 실제 Nginx에서 수행합니다.

    python3 -m unittest discover -s tests -p test_site.py -v
    python3 scripts/verify_publication.py

로컬에 Playwright·Chromium이 설치되어 있으면 각 공개 상태의 브라우저 검사도 실행할 수 있습니다.

    python3 scripts/verify_publication.py --browser

검사는 임시 복사본에서 공개 0개부터 전체 공개까지 빌드하고 별도 로컬 컨테이너를 사용합니다. 저장소 공개 설정이나 운영 서비스는 수정하지 않습니다. 상세 결과와 제한은 [docs/VALIDATION.md](docs/VALIDATION.md)에 기록합니다.

## 빌드와 미공개 파일 제외

Docker의 Python 빌드 단계가 `media.json`을 읽어 공개 파일만 `dist/site`에 복사합니다. 최종 이미지는 기존 Nginx 기반이며 Python이나 원본 보관 디렉터리를 포함하지 않습니다. MP4·포스터는 원본 바이트 그대로 복사합니다. HTML과 reel 라우팅 맵도 동일 설정에서 생성합니다.

각 빌드는 출력을 비우고 새로 만들므로 과거 HTML·MP4·포스터가 남지 않습니다. 미공개 파일은 최종 정적 디렉터리에 없어 직접 요청도 404입니다. source인 public 디렉터리는 최종 이미지에 통째로 복사하지 않습니다. 영상 URL `/videos/<기존 파일명>.mp4`와 포스터 URL은 유지하고 내용 SHA-256의 버전 쿼리를 사용합니다. 기본 HTML과 개별 HTML은 no-store, 버전 있는 미디어는 기존 immutable 캐시 정책을 유지합니다.

생성 HTML은 커밋하지 않으며 직접 편집하지 않습니다. 예전 `/video-1.html` 등 주소도 동일한 공개 상태를 적용한 한 편 전용 페이지로 유지합니다.

## 영상 교체·새 영상 추가

기존 영상 교체는 정확한 원본 파일을 `video` 경로에 그대로 복사한 뒤 아래 명령으로 해당 영상만 검사·포스터 추출합니다. MP4는 재인코딩하지 않습니다.

    python3 scripts/refresh_media.py --reel responsibility

추가 릴스 1~2개도 같은 방식으로 등록할 수 있습니다.

1. 실제 MP4를 제공받아 public/videos/에 새 영문 파일명으로 보관합니다. 기존 파일·ID·발송 링크를 재사용하지 않습니다.
2. `media.json` 끝에 새 항목을 추가합니다. 고유 `id`, 고유 `reel_id`, 실제 제목(label), source_name, video, poster, send_date를 입력하고 **published는 false**로 둡니다. 아직 없는 영상을 등록하거나 빈 카드를 만들지 않습니다.
3. `python3 scripts/refresh_media.py --reel <새 reel_id>`로 실제 메타데이터·SHA-256·첫 화면 포스터를 생성하고 선명한 화면인지 검수합니다. 다른 영상의 포스터는 재생성하지 않습니다.
4. 빌드·검사·PR·수동 병합/배포 절차로 등록하고, 공개할 때만 published를 true로 바꾸어 다시 배포합니다.
5. 개별 링크는 `현재 사이트 주소/?reel=<새 reel_id>`입니다. 기존 영상의 링크와 연결은 유지됩니다.

새 라우팅은 설정에서 자동 생성되므로 Nginx에 ID를 수동 추가할 필요가 없습니다. 영상 제작·편집 기능은 없습니다.

## Cloudtype 설정 유지

기존 별도 서비스의 저장소 OpenEntry921/laity_shorts, 수동 병합 후 main, 루트 Dockerfile, 빌드 컨텍스트 저장소 루트, **HTTP 8080**을 사용합니다. 시작 명령은 이미지 기본값인 nginx 포그라운드 실행을 유지합니다. 별도 환경변수·DB·디스크는 필요 없습니다.

비루트 UID/GID 101:101과 등록되지 않은 숫자 UID/GID를 지원합니다. nginx-main.conf의 PID와 다섯 임시 경로는 /tmp 아래이고 로그는 표준 출력·오류입니다. 읽기 전용 루트에서는 실행 UID가 쓸 수 있는 /tmp가 필요합니다. 기본 entrypoint 초기화나 런타임 설정 수정은 사용하지 않습니다.

도메인 구매·DNS 변경 없이 기존 기본 HTTPS 주소를 사용합니다. 새 서비스가 필요할 때만 Cloudtype에서 별도 서비스를 추가하고 기본 HTTPS 주소를 확인하세요. 기존 서비스를 삭제·분할·이전하지 않습니다. 새 서비스 자원이 기존 요금제에서 자동 분할된다고 가정하지 않습니다.

noindex/nofollow는 검색 노출 제한 지시이며 접근 제한 기능은 아닙니다. 외부 폰트·분석·추적 스크립트는 없습니다. 이번 작업에서는 Cloudtype 서비스·요금제·환경변수·도메인·DNS를 변경하지 않습니다.
