# 개발 및 검증

앱은 정적 HTML·CSS·JavaScript와 Nginx만 사용합니다. 개별 링크의 첫 영상 선택은 Nginx의 reel 쿼리 매핑으로 처리합니다. 모든 페이지에 세 영상이 있으며 JavaScript는 CSS 정렬과 초기 위치 조정 후 피드를 표시합니다. JavaScript 없이도 요청한 영상부터 세 영상의 기본 조작이 남습니다. Python 스크립트는 개발 시 페이지·버전 URL을 생성하는 도구이며 운영 이미지에는 포함하지 않습니다.

검색 억제는 robots 메타·X-Robots-Tag의 noindex/nofollow와 robots.txt로 설정합니다. 이는 접근 제한이나 인증 기능이 아니며 링크를 가진 사람은 영상을 열람할 수 있습니다. 이 설명은 개발 문서에만 둡니다.

## 원본 검증

이번 첨부는 세 파일 모두 H.264 406×720, 약 56.958005초이며 AAC 2채널 오디오 트랙이 있습니다. 원본 해상도·길이·화면·오디오를 유지했습니다. 업로드 순서 대신 실제 화면을 보고 매칭했습니다. 파일명 물음표는 업로드 저장 과정에서 밑줄로 바뀌었지만 세 번째 영상의 실제 내용을 확인했습니다. 포스터는 각 영상 2초 지점의 선명한 첫 화면에서 추출했습니다.

| 원본 식별 | 배포 파일 | 크기(bytes) | SHA-256 |
| --- | --- | --- | --- |
| 권한에책임이뒤따릅니다.mp4 | public/videos/responsibility.mp4 | 1,770,216 | d68992e2ac642092dee5deca8a167fc41f9509f523a678d8d1a24afc72cc2ae1 |
| 본질을훼손마세요.mp4 | public/videos/offering.mp4 | 1,677,798 | 4f4a5b2d377e129ee05d8cd009c97b0d60db2cc846dbab6c643d2fa952c450ae |
| 누가매일나오랍니까_.mp4 | public/videos/example.mp4 | 1,526,894 | dc670f192f40e0c3d6a45af3ef1de542b1b54ece7de10bde7644ae5c19d058b6 |

media.json과 테스트가 원본 크기·체크섬 및 생성된 HTML의 최신 상태를 검증합니다. MP4와 포스터의 내용 해시를 쿼리 버전으로 사용합니다. HTML은 no-store, 버전이 없는 영상은 no-cache로 재검증하고, 해시 버전 영상/포스터는 장기 캐시합니다. 교체 후 생성 스크립트를 실행하면 HTML이 새 URL을 참조합니다.

## 재현 명령

    python3 scripts/build.py
    node --check public/player.js
    docker build -t laity-shorts:review .
    docker run --rm --entrypoint nginx laity-shorts:review -t
    docker run --rm -p 18080:8080 laity-shorts:review

서버가 실행된 다른 터미널에서:

    python3 -m unittest discover -s tests -v

Playwright와 Chromium이 있는 개발 환경에서:

    SHORTS_ARTIFACTS=/tmp/shorts-artifacts node tests/browser.cjs

Playwright가 없다면 별도 도구 디렉터리에 설치하고 NODE_PATH를 지정할 수 있습니다. 앱 의존성은 추가하지 않습니다. 브라우저 위치는 CHROMIUM_PATH, 대상은 SHORTS_BASE_URL로 바꿀 수 있습니다. CI는 Docker 빌드·Nginx 설정과 Python/HTTP 검사를 수행합니다. 브라우저 검사는 별도 개발 검사입니다.

## 실행 결과

- Docker 이미지 빌드 및 Nginx 설정 검사 통과.
- Python 정적 파일/HTTP 테스트 6개 통과: 원본 SHA-256·크기, 생성 페이지 최신 상태, 기본/개별/잘못된 쿼리, MIME, 200 전체 응답·206 Range 바이트, 포스터, 캐시 정책과 실제 404 포함.
- Chromium의 360×800 / 390×844 / 844×390 / 1440×1000에서 기본 화면·reel=responsibility/essence/prayer·잘못된 값 확인. 첫 화면의 재생 버튼은 64px 이상이며 가려지지 않음. 가로 스크롤 없음, object-fit: contain으로 전체 영상 표시.
- 각 크기에서 세 실제 MP4의 재생·일시정지·10초 탐색·전체화면 통과. 새 영상이 시작되면 다른 두 영상 일시정지 확인. 키보드 Enter 재생 확인.
- 초기 화면별 MP4 요청 0건. 화면 진입 검사에서 외부 요청·실패 응답·콘솔 오류 없음.
- JavaScript 비활성 상태에서 reel=prayer 요청 영상이 먼저 나오고, 세 영상과 기본 video controls가 유지됨을 확인.
- 의도적으로 미디어 응답을 실패시킨 검사에서 지정된 오류 안내만 표시됨. 다시 실제 응답을 허용한 후 재시도로 재생 복구 확인.
- 실제 휴대전화·카카오톡 내부 브라우저·실제 Cloudtype HTTPS 배포는 미확인. 브라우저 검사는 로컬 Nginx Docker 이미지에서 수행.
- 다른 저장소, 기존 서비스·도메인·Cloudtype 설정은 변경하지 않음. 실제 배포·자동 병합 없음.

[모바일](screenshots/mobile.png) · [가로 화면](screenshots/landscape.png) · [PC 개별 링크](screenshots/desktop-single.png)

## 스크롤 피드·공유 링크 변경 검증

- Docker 빌드, nginx -t와 기존 비루트/읽기 전용 루트/숫자 UID 12345:23456 실행 조건 유지.
- Python/HTTP 테스트 6개 통과. 모든 HTML의 세 원본 포함·서로 다른 체크섬, reel 매핑·무효 값 fallback, MIME·Range 206·캐시 검사 포함.
- Chromium 360×800 / 390×844 / 844×390 / 1440×1000에서 기본·개별 링크 직접 접속과 새로고침, 첫 가시 프레임의 대상 영상, 화면 방향/크기 변경 확인.
- 모바일 크기는 CDP 터치 스와이프 시뮬레이션, PC는 마우스 휠로 다음/이전 스냅 이동 확인. 실제 휴대전화 검사가 아님.
- 각 화면 크기에서 세 영상의 재생·일시정지·탐색·전체화면 및 화면 이탈 시 이전 영상 정지 확인.
- 현재 영상 URL이 replaceState로 바뀌고 스크롤 왕복에도 history.length가 늘지 않음을 확인.
- 초기 MP4 요청 0건, 정상 경로 콘솔·요청 오류와 가로 넘침 없음. JavaScript 없는 서버 fallback과 의도적 404 후 재시도 복구 확인.
- MP4·포스터·media.json, Dockerfile·nginx-main.conf와 비루트 CI 실행 조건은 수정하지 않음.
- 실제 Cloudtype 접속은 프록시 CONNECT 403으로 미확인. 실제 모바일·카카오톡 내부 브라우저·원격 CI·병합/배포 결과도 미확인.
- 대응표·예정 링크·문자 예시는 [공유 안내](SHARING.md)를 참고.
