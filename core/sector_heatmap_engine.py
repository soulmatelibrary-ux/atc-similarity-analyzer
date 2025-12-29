"""
섹터 히트맵 생성 엔진
- 섹터 좌표를 기반으로 다각형 그리기
- 어느 섹터에서 유사호출이 많이 발생하는지 시각화
- 위험도별 컬러 매핑
"""
import json
from utils.logger import setup_logger
from utils.constants import RISK_COLORS, SECTORS

logger = setup_logger(__name__)


class SectorHeatmapEngine:
    """섹터 히트맵 생성 엔진"""

    def __init__(self, sector_coords=None):
        """
        초기화

        Args:
            sector_coords: 섹터별 좌표 정보 (딕셔너리)
        """
        self.sector_coords = sector_coords or {}
        self.similarity_data = {}  # 섹터별 유사호출 데이터

    def add_similarity_event(self, sector, lat, lon, callsign1, callsign2,
                            similarity_level, risk_level, coexist_minutes):
        """
        유사호출 이벤트 추가

        Args:
            sector: 섹터 코드 (예: 'JH', 'JN')
            lat: 위도
            lon: 경도
            callsign1: 첫 번째 콜사인
            callsign2: 두 번째 콜사인
            similarity_level: 유사도 레벨
            risk_level: 위험도
            coexist_minutes: 공존 시간 (분)
        """
        if sector not in self.similarity_data:
            self.similarity_data[sector] = {
                'events': [],
                'risk_counts': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
                'total_events': 0,
                'avg_coexist': 0,
            }

        event = {
            'callsign1': callsign1,
            'callsign2': callsign2,
            'lat': lat,
            'lon': lon,
            'similarity_level': similarity_level,
            'risk_level': risk_level,
            'coexist_minutes': coexist_minutes,
        }

        self.similarity_data[sector]['events'].append(event)
        self.similarity_data[sector]['risk_counts'][risk_level] += 1
        self.similarity_data[sector]['total_events'] += 1

    def generate_heatmap_data(self):
        """
        히트맵 데이터 생성

        Returns:
            dict: 히트맵 렌더링을 위한 데이터
        """
        heatmap_data = {
            'sectors': {},
            'global_stats': {
                'total_events': 0,
                'total_sectors': len(self.similarity_data),
                'high_risk_count': 0,
                'medium_risk_count': 0,
                'low_risk_count': 0,
            }
        }

        for sector, data in self.similarity_data.items():
            # 위험도 비율 계산
            total = data['total_events']
            high_ratio = data['risk_counts']['HIGH'] / total if total > 0 else 0
            medium_ratio = data['risk_counts']['MEDIUM'] / total if total > 0 else 0

            # 평균 공존시간 계산
            avg_coexist = sum(e['coexist_minutes'] for e in data['events']) / total if total > 0 else 0

            sector_info = {
                'name': sector,
                'event_count': total,
                'risk_distribution': {
                    'HIGH': data['risk_counts']['HIGH'],
                    'MEDIUM': data['risk_counts']['MEDIUM'],
                    'LOW': data['risk_counts']['LOW'],
                },
                'high_risk_ratio': high_ratio,
                'medium_risk_ratio': medium_ratio,
                'avg_coexist_minutes': round(avg_coexist, 1),
                'intensity': self._calculate_intensity(total),  # 0-100
                'color': self._get_heatmap_color(high_ratio, medium_ratio),
                'events': data['events'][:100],  # 처음 100개 이벤트만
            }

            heatmap_data['sectors'][sector] = sector_info

            # 전역 통계 업데이트
            heatmap_data['global_stats']['total_events'] += total
            heatmap_data['global_stats']['high_risk_count'] += data['risk_counts']['HIGH']
            heatmap_data['global_stats']['medium_risk_count'] += data['risk_counts']['MEDIUM']
            heatmap_data['global_stats']['low_risk_count'] += data['risk_counts']['LOW']

        return heatmap_data

    def _calculate_intensity(self, event_count, max_events=100):
        """
        이벤트 개수로부터 히트맵 강도 계산 (0-100)

        Args:
            event_count: 이벤트 개수
            max_events: 최대 이벤트 개수 (기준값)

        Returns:
            int: 강도 (0-100)
        """
        intensity = min(int((event_count / max_events) * 100), 100)
        return max(intensity, 1)  # 최소 1

    def _get_heatmap_color(self, high_ratio, medium_ratio):
        """
        위험도 비율에 따른 히트맵 색상 결정

        Args:
            high_ratio: HIGH 비율
            medium_ratio: MEDIUM 비율

        Returns:
            str: RGB 색상 코드 또는 HEX 색상
        """
        # 위험도가 높을수록 빨간색, 낮을수록 초록색
        if high_ratio >= 0.5:
            return '#ff0000'  # 빨강 (매우 위험)
        elif high_ratio >= 0.3:
            return '#ff6b6b'  # 밝은 빨강 (위험)
        elif high_ratio + medium_ratio >= 0.7:
            return '#ffd43b'  # 노랑 (중간 위험)
        else:
            return '#51cf66'  # 초록 (안전)

    def generate_sector_polygon_json(self):
        """
        섹터 다각형을 GeoJSON 형식으로 생성

        Returns:
            dict: GeoJSON FeatureCollection
        """
        features = []

        for sector, data in self.similarity_data.items():
            # 섹터별 다각형 좌표
            coordinates = self.sector_coords.get(sector, [])

            if not coordinates:
                logger.warning(f"섹터 {sector}의 좌표 정보 없음")
                continue

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [coordinates]  # 폐곡선
                },
                'properties': {
                    'sector': sector,
                    'event_count': data['total_events'],
                    'intensity': self._calculate_intensity(data['total_events']),
                    'color': self._get_heatmap_color(
                        data['risk_counts']['HIGH'] / max(data['total_events'], 1),
                        data['risk_counts']['MEDIUM'] / max(data['total_events'], 1)
                    ),
                    'high_risk': data['risk_counts']['HIGH'],
                    'medium_risk': data['risk_counts']['MEDIUM'],
                    'low_risk': data['risk_counts']['LOW'],
                }
            }
            features.append(feature)

        return {
            'type': 'FeatureCollection',
            'features': features
        }

    def generate_html_heatmap(self, title="유사호출 히트맵"):
        """
        HTML 기반 히트맵 생성 (Folium 또는 Plotly 사용)

        Args:
            title: 제목

        Returns:
            str: HTML 코드
        """
        heatmap_data = self.generate_heatmap_data()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                }}
                .stats {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin-bottom: 30px;
                }}
                .stat-box {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .stat-box h3 {{
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .stat-box .value {{
                    font-size: 28px;
                    font-weight: bold;
                }}
                .heatmap-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 15px;
                    margin-top: 20px;
                }}
                .sector-card {{
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    transition: transform 0.2s;
                }}
                .sector-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}
                .sector-name {{
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .sector-bar {{
                    background: linear-gradient(90deg, #ff0000, #ffd43b, #51cf66);
                    height: 30px;
                    border-radius: 4px;
                    position: relative;
                    margin: 10px 0;
                }}
                .sector-bar-fill {{
                    height: 100%;
                    border-radius: 4px;
                    transition: width 0.3s;
                }}
                .risk-legend {{
                    display: flex;
                    gap: 20px;
                    margin-top: 20px;
                    justify-content: center;
                }}
                .legend-item {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                .legend-color {{
                    width: 20px;
                    height: 20px;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{title}</h1>

                <div class="stats">
                    <div class="stat-box">
                        <h3>총 유사호출 이벤트</h3>
                        <div class="value">{heatmap_data['global_stats']['total_events']}</div>
                    </div>
                    <div class="stat-box">
                        <h3>영향 섹터</h3>
                        <div class="value">{heatmap_data['global_stats']['total_sectors']}</div>
                    </div>
                    <div class="stat-box">
                        <h3>고위험</h3>
                        <div class="value">{heatmap_data['global_stats']['high_risk_count']}</div>
                    </div>
                    <div class="stat-box">
                        <h3>중위험</h3>
                        <div class="value">{heatmap_data['global_stats']['medium_risk_count']}</div>
                    </div>
                </div>

                <div class="risk-legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #ff0000;"></div>
                        <span>고위험 (50% 이상)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #ffd43b;"></div>
                        <span>중위험 (30-50%)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #51cf66;"></div>
                        <span>저위험 (30% 이하)</span>
                    </div>
                </div>

                <div class="heatmap-grid">
"""

        # 섹터별 카드 생성
        for sector, sector_data in heatmap_data['sectors'].items():
            html += f"""
                    <div class="sector-card" style="border-left: 4px solid {sector_data['color']};">
                        <div class="sector-name">{sector}</div>
                        <div style="font-size: 12px; color: #666;">
                            이벤트: {sector_data['event_count']}개<br/>
                            평균 공존시간: {sector_data['avg_coexist_minutes']}분
                        </div>
                        <div class="sector-bar" style="background-color: #f0f0f0;">
                            <div class="sector-bar-fill" style="
                                width: {sector_data['intensity']}%;
                                background-color: {sector_data['color']};
                            "></div>
                        </div>
                        <div style="font-size: 11px; color: #999;">
                            <span style="color: #ff0000;">●</span> {sector_data['risk_distribution']['HIGH']}
                            <span style="color: #ffd43b;">●</span> {sector_data['risk_distribution']['MEDIUM']}
                            <span style="color: #51cf66;">●</span> {sector_data['risk_distribution']['LOW']}
                        </div>
                    </div>
"""

        html += """
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def save_heatmap_html(self, filename='heatmap.html'):
        """
        히트맵을 HTML 파일로 저장

        Args:
            filename: 저장할 파일명
        """
        html = self.generate_html_heatmap()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"히트맵 HTML 저장: {filename}")

    def save_heatmap_json(self, filename='heatmap.json'):
        """
        히트맵 데이터를 JSON으로 저장

        Args:
            filename: 저장할 파일명
        """
        data = self.generate_heatmap_data()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"히트맵 JSON 저장: {filename}")


# 테스트용 함수
def create_sample_heatmap():
    """샘플 히트맵 생성"""
    engine = SectorHeatmapEngine()

    # 샘플 데이터 추가
    engine.add_similarity_event('JH', 37.2, 127.1, 'GIA878', 'AIA878', 'LEVEL_2-1', 'HIGH', 25)
    engine.add_similarity_event('JH', 37.3, 127.0, 'GIA123', 'AIA124', 'LEVEL_3-8', 'HIGH', 15)
    engine.add_similarity_event('JN', 37.5, 127.5, 'KAL456', 'AAL457', 'LEVEL_2-2', 'MEDIUM', 10)
    engine.add_similarity_event('KH', 36.8, 128.0, 'OZ001', 'OZ002', 'LEVEL_3-1', 'LOW', 5)

    # HTML 저장
    engine.save_heatmap_html()
    engine.save_heatmap_json()

    return engine


if __name__ == '__main__':
    engine = create_sample_heatmap()
    print("✓ 히트맵 생성 완료: heatmap.html, heatmap.json")
