# 순차 발송·개별 영상 전용 페이지 검증

기준 main: `b3968f2`. 사용자 선택은 세 페이지를 미리 공개하고 2026년 11월 17·19·21일(한국시간)에 링크만 따로 보내는 방식입니다. `media.json`의 세 published 값은 true입니다. 이는 **병합·배포 후 적용 예정 설정**이며 실제 운영 확인이 아닙니다. 운영 주소는 프록시 CONNECT 403으로 접근할 수 없었습니다.

## 원본 확인

파일 내용의 첫 화면과 기존 원본 SHA-256을 대조했습니다. 세 영상은 서로 다른 원본이고 길이 약 56.958초, 406×720 H.264, AAC 오디오 스트림이 있습니다. 원본 MP4·포스터 바이트는 변경하지 않았습니다.

| reel_id | 원본 파일 | SHA-256 |
| --- | --- | --- |
| responsibility | responsibility.mp4 | d68992e2ac642092dee5deca8a167fc41f9509f523a678d8d1a24afc72cc2ae1 |
| essence | offering.mp4 | 4f4a5b2d377e129ee05d8cd009c97b0d60db2cc846dbab6c643d2fa952c450ae |
| prayer | example.mp4 | dc670f192f40e0c3d6a45af3ef1de542b1b54ece7de10bde7644ae5c19d058b6 |

## 격리된 공개 상태 검사

`python3 scripts/verify_publication.py --browser`를 실행했습니다.

각 상태는 임시 빌드 컨텍스트의 설정으로 실제 Docker 이미지를 만들었습니다. 저장소 공개 설정이나 Cloudtype 환경을 검사 때문에 변경하지 않았습니다.

| 공개 상태 | nginx -t | HTTP·파일·캐시·Range | 최종 이미지 파일 목록 | 숫자 UID/읽기 전용 실행 | 브라우저 |
| --- | --- | --- | --- | --- | --- |
| 0개 | 통과 | 통과 | 통과 | 통과 | 통과 |
| responsibility만 | 통과 | 통과 | 통과 | 통과 | 통과 |
| responsibility + essence | 통과 | 통과 | 통과 | 통과 | 통과 |
| 세 편 모두 | 통과 | 통과 | 통과 | 통과 | 통과 |

각 이미지에서 수행:

- 기본/개별/잘못된 쿼리·빈 값·대문자 값·기존 정적 video-N.html 확인. 개별 페이지는 해당 한 편 또는 미공개 안내만 반환하고 다른 제목·포스터·재생 주소가 없습니다.
- 미공개 MP4·포스터 없음 및 직접 URL/구버전 쿼리 URL 404 확인. 공개 MP4는 video/mp4, 원본 SHA-256과 동일한 전체 바이트, Range 206·정확한 Content-Range 및 해당 바이트 일치. 포스터는 원본 바이트와 동일.
- 최종 이미지의 정적 파일 목록과 /build 디렉터리 부재 확인. HTML no-store, 기존 미디어 no-cache/버전 immutable 및 noindex/nofollow·CSP 유지.
- UID/GID 12345:23456(이미지에 등록되지 않은 숫자), 읽기 전용 루트, 쓰기 가능한 /tmp mode0700, cap-drop ALL, no-new-privileges에서 실행. 컨테이너 running=true/restarts=0 확인. 포트 8080 유지.
- Chromium 360×800, 390×844, 1440×1000, 844×390. 상태마다 20개 경로/크기 조합, 총 80개 확인. 직접 접속·새로고침·공개 개수·단독 화면·안내 화면·가로 넘침 없음·초기 MP4 요청 0건·정상 경로 콘솔/요청 오류 없음.
- 실제 공개 MP4의 키보드 재생·일시정지·10초 탐색·전체화면·contain 확인. 기본 화면의 터치 스와이프 시뮬레이션/마우스 휠 전후 이동, 이전 영상 정지·동시 재생 방지 확인. 개별 화면은 넘겨도 다른 영상이 나타나지 않음.
- JavaScript 비활성 상태의 한 편 기본 controls 확인. 의도적 404 후 오류 안내 및 재시도 재생 복구 확인. 0개 공개 상태는 재생 검사가 적용되지 않습니다.

Python 빌드 검사 5개도 통과했습니다. 동일 출력 디렉터리를 공개 3→0→2→1개로 연속 재생성하여 과거 파일 제거를 확인했고, published 생략·과거 날짜에도 미공개 유지, 중복 ID/잘못된 경로/무결성 오류 시 실패를 검사했습니다. 추가 릴스 등록은 임시 복사본의 명시적인 라우팅 fixture로만 검사했습니다. 제품에 가짜 추가 영상이나 빈 카드는 없습니다.

## 재현과 제한

실행 명령은 README를 참고하세요. HTTP 테스트는 실행할 실제 Nginx를 대상으로 `SHORTS_BASE_URL`, 다른 격리 설정은 `SHORTS_MANIFEST`를 지정할 수 있습니다. 기본 unittest 전체 실행은 현재 설정으로 실행한 18080 포트의 Nginx가 필요합니다.

원격 GitHub Actions, 실제 Cloudtype 배포·운영 HTTPS/CDN, 실제 휴대전화·카카오톡 내부 브라우저는 미확인입니다. 모바일 검사는 Chromium 화면 크기와 CDP 터치 시뮬레이션입니다. 로컬 Docker 성공을 운영 배포 성공으로 보고하지 않습니다.

다른 저장소 shinsung, laity.kr, /prepare와 Cloudtype 서비스·요금제·환경변수·도메인·DNS는 변경하지 않았습니다. main 직접 푸시·병합·배포는 실행하지 않았습니다. 병합·배포 후 사용자가 세 개별 주소가 한 편만 표시하는지와 기본 주소의 공개 목록을 실제 기기에서 확인해야 합니다.

[모바일 개별 페이지](screenshots/mobile.png) · [가로 개별 페이지](screenshots/landscape.png) · [PC 개별 페이지](screenshots/desktop-single.png)
