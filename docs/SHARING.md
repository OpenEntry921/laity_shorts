# 릴스 링크와 검증

## 병합·배포 후 사용할 예정 링크

아직 배포하지 않았으며 실제 운영 주소에서 새 동작을 확인하지 않았습니다. 아래 주소는 사용자가 제공한 현재 Cloudtype HTTPS 주소를 그대로 사용합니다. 새 도메인이나 DNS 변경은 없습니다.

| ID | 실제 영상 제목·내용 | 파일 | 예정 링크 |
| --- | --- | --- | --- |
| responsibility | 권한에 책임이 뒤따릅니다: 권한·책임과 교회 운영에 관한 질문 | public/videos/responsibility.mp4 | https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=responsibility |
| essence | 본질을 훼손마세요: 목적헌금·원심 판단·소명·복직 | public/videos/offering.mp4 | https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=essence |
| prayer | 누가 매일 나오라고 합니까?: 예배·기도·사역 참여 | public/videos/example.mp4 | https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=prayer |

목적헌금 원본에서는 십일조 장면을 확인하지 못했습니다. 해당 내용이 포함되었다고 표기하거나 다른 영상으로 채우지 않았습니다. 세 파일은 서로 다른 기존 원본이며 MP4와 포스터·media.json의 바이트는 변경하지 않습니다.

## 문자 발송 예시

일반 SMS는 문구 자체에 숨겨진 링크를 넣는 방식이 아니라, 다음처럼 문구와 실제 URL을 줄바꿈해 보냅니다. 아래 링크도 병합·배포 후 사용할 예정 주소입니다.

    권한과 책임에 관한 릴스입니다.
    https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=responsibility

    목적헌금의 본질에 관한 릴스입니다.
    https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=essence

    예배와 사역 참여에 관한 릴스입니다.
    https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app/?reel=prayer

## 구현과 확인 방법

Nginx는 reel 쿼리를 기존 정적 HTML 파일에 매핑합니다. 모든 HTML에 세 영상이 있으며, 개별 페이지의 서버 HTML은 요청한 영상을 먼저 둡니다. JavaScript는 첫 표시 전 가림 처리 안에서 원래 순서로 정렬하고 요청한 위치에 맞춘 뒤 화면을 보여줍니다. 따라서 첫 번째 영상이 잠깐 나타나지 않으며, 공유한 영상의 위·아래에 있는 영상도 볼 수 있습니다. JavaScript가 없는 경우에도 요청한 영상부터 세 영상과 기본 controls가 남습니다.

화면 높이의 내부 스크롤 영역에 CSS scroll-snap을 사용하고 dvh/safe-area에 대응합니다. 보이는 릴스가 바뀌면 이전 영상을 일시정지하고 window.location.origin 기반 URL을 replaceState로 갱신합니다. 자동재생은 추가하지 않았습니다.

로컬 검증:

    python3 scripts/build.py
    docker build -t laity-shorts:reel-links .
    docker run --rm --read-only --tmpfs /tmp:rw,nosuid,noexec,uid=101,gid=101,mode=0700 laity-shorts:reel-links -t
    docker run --rm --user 12345:23456 --read-only --tmpfs /tmp:rw,nosuid,noexec,uid=12345,gid=23456,mode=0700 --cap-drop=ALL --security-opt=no-new-privileges -p 18080:8080 laity-shorts:reel-links

다른 터미널:

    python3 -m unittest discover -s tests -v
    SHORTS_ARTIFACTS=/tmp/reel-artifacts node tests/browser.cjs

실제 휴대전화·카카오톡 내부 브라우저 검사는 별도입니다. 이 환경에서는 운영 주소에 대한 연결이 프록시 CONNECT 403으로 차단되어 운영 페이지를 읽지 못했습니다. 이를 운영 서비스 자체의 오류나 새 코드의 배포 확인으로 해석하지 않습니다.
