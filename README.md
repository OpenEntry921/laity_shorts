# laity_shorts

## 로컬 실행

Docker가 필요합니다. 저장소 루트에서 실행합니다.

    docker build -t laity-shorts .
    docker run --rm -p 8080:8080 laity-shorts

브라우저에서 http://localhost:8080 으로 접속합니다. 이미지는 비루트 UID/GID 101:101로 실행되며 플랫폼이 다른 숫자 UID/GID를 지정해도 동작합니다. Python 기본 파일 서버는 개별 영상의 쿼리 라우팅과 Range 검증을 대신하지 않습니다.

## Cloudtype에 새 서비스 추가

GitHub 연결 후 **새로운 서비스/애플리케이션**을 만들고 이 저장소의 Dockerfile로 배포합니다. 기존 서비스나 도메인을 삭제·분할·이전하지 않습니다. 새 서비스에는 별도 자원이 필요할 수 있으며 기존 요금제가 자동 분할된다고 가정하지 않습니다.

## 저장소·브랜치·Dockerfile·포트

- 저장소: OpenEntry921/laity_shorts
- 브랜치: 수동 병합 후 main
- Dockerfile: 저장소 루트의 Dockerfile, 빌드 컨텍스트도 저장소 루트
- 노출 포트: 8080 / HTTP
- 시작 명령: 이미지 기본값 사용 (nginx를 daemon off로 직접 실행)
- 별도 환경변수·DB·영구 디스크·외부 API 설정 없음

설정 파일은 이미지 빌드 시 고정됩니다. nginx-main.conf는 전역 프로세스 설정, 기존 nginx.conf는 사이트 설정입니다. 런타임 설정 변경 스크립트나 환경변수 치환이 필요하지 않습니다. root 실행·추가 권한 없이 PID와 다섯 임시 디렉터리만 /tmp 아래에 생성하므로, 읽기 전용 루트 파일시스템에서도 /tmp는 실행 UID가 쓸 수 있어야 합니다. 기본 이미지의 entrypoint 초기화는 사용하지 않으며 별도 시작 명령을 지정할 필요가 없습니다. 오류 로그는 표준 오류, 전역 접근 로그는 표준 출력으로 보냅니다. 사이트의 기존 접근 로그 비활성 설정은 유지합니다.

## 기본 HTTPS 주소 확인

배포 완료 후 **새 서비스** 화면에 표시되는 Cloudtype 기본 HTTPS 접속 주소를 복사합니다. 별도 도메인 구매나 기존 도메인 변경은 필요 없습니다.

## 개별 영상 링크

현재 사용하는 기본 HTTPS 주소는 다음과 같습니다. 아래 변경은 수동 병합·배포 후 적용됩니다. 이번 작업에서는 배포하지 않았으며 운영 주소의 새 동작은 아직 확인하지 않았습니다.

https://port-0-laity-shorts-mv4itaiva5851d33.sel3.cloudtype.app

| 경로 | 처음 표시할 영상 | 파일 |
| --- | --- | --- |
| / | 권한과 책임부터 순서대로 3개 | 전체 |
| /?reel=responsibility | 권한에 책임이 뒤따릅니다 | public/videos/responsibility.mp4 |
| /?reel=essence | 본질을 훼손마세요 | public/videos/offering.mp4 |
| /?reel=prayer | 누가 매일 나오라고 합니까? | public/videos/example.mp4 |

개별 링크도 세 영상을 모두 포함합니다. 모바일은 위아래 스와이프, PC는 휠·터치패드로 이전/다음 영상으로 이동합니다. 현재 영상이 바뀌면 주소를 replaceState로 갱신하며 뒤로가기 기록은 늘리지 않습니다. reel이 없거나 잘못되면 첫 번째 영상부터 표시합니다. 기존 숫자 v 쿼리는 영상 선택에 사용하지 않습니다.

현재 목적헌금 원본의 확인된 내용은 목적헌금·원심 판단·소명·복직입니다. 십일조 장면은 확인되지 않았으며 영상을 편집하거나 다른 파일로 대체하지 않았습니다.

문자 공유 문안과 전체 예정 링크는 docs/SHARING.md에 있습니다.

## 영상 교체

새 원본을 public/videos/responsibility.mp4, offering.mp4, example.mp4에 대응시켜 그대로 복사합니다. MP4를 재인코딩하지 않습니다. 개발 컴퓨터에 Python 3·FFmpeg가 있으면 다음 명령으로 메타데이터·체크섬·첫 화면 포스터·페이지의 캐시 버전을 갱신합니다.

    python3 scripts/refresh_media.py

media.json의 원본 식별명(source_name)도 새 첨부명으로 갱신하고 포스터가 선명한 첫 화면인지 확인합니다. 필요하다면 해당 포스터만 가까운 선명한 프레임으로 다시 추출한 뒤 python3 scripts/build.py를 실행합니다. 변경 파일을 커밋하고 새 이미지를 배포하면 됩니다. 생성된 HTML을 직접 편집하거나 오래된 영상 URL을 하드코딩하지 않습니다.
