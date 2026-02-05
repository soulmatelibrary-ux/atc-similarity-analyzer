"""
비행계획서 모델링 테스트 GUI (tkinter)
독립 실행 가능한 Python GUI 애플리케이션
"""

import os
import sys
import json
from datetime import datetime, date
from tkinter import (
    Tk, Toplevel, Frame, Label, Entry, Text, Button,
    Scrollbar, messagebox, filedialog, StringVar,
    ttk, END, VERTICAL, HORIZONTAL, BOTH, LEFT, RIGHT, TOP, BOTTOM,
    X, Y, W, E, N, S, NW, NE, SW, SE, WORD, DISABLED, NORMAL
)

# 상위 디렉토리를 경로에 추가 (코어 모듈 import용)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

# 코어 모듈 import
try:
    from core.flight_processor import calculate_trajectory
    from core.modeling_resources import get_modeling_resources
    from core.fix_time_converter import (
        convert_fixtime_to_json,
        get_conversion_statistics,
        save_json_file,
        load_json_file,
        flatten_fix_times,
        update_fix_time,
        delete_fix_time
    )
    from core.waypoint_calculator import _reload_fix_travel_lookup
    from database.db_manager import DatabaseManager
except ImportError as e:
    print(f"코어 모듈 import 오류: {e}")
    print("상위 디렉토리에 core/, database/ 폴더가 있는지 확인하세요.")
    sys.exit(1)


class ModelingTestGUI:
    """비행계획서 모델링 테스트 GUI 메인 클래스"""

    def __init__(self, root):
        self.root = root
        self.root.title("비행계획서 모델링 테스트")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # 데이터 초기화
        self.resources = None
        self.db_manager = None
        self.fix_times_data = []

        # 스타일 설정
        self.setup_styles()

        # UI 구성
        self.create_widgets()

        # 리소스 로드
        self.load_resources()

    def setup_styles(self):
        """ttk 스타일 설정"""
        style = ttk.Style()
        style.theme_use('clam')

        # 버튼 스타일
        style.configure('Primary.TButton', background='#667eea', foreground='white')
        style.configure('Success.TButton', background='#28a745', foreground='white')
        style.configure('Danger.TButton', background='#dc3545', foreground='white')

    def create_widgets(self):
        """위젯 생성"""
        # 메인 노트북 (탭)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # 탭 1: 모델링 테스트
        self.modeling_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modeling_frame, text="  모델링 테스트  ")
        self.create_modeling_tab()

        # 탭 2: FIX 이동시간 관리
        self.fix_times_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.fix_times_frame, text="  FIX 이동시간 관리  ")
        self.create_fix_times_tab()

    def create_modeling_tab(self):
        """모델링 테스트 탭 UI"""
        # 좌우 분할
        paned = ttk.PanedWindow(self.modeling_frame, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True)

        # === 왼쪽: 입력 폼 ===
        input_frame = ttk.LabelFrame(paned, text=" 비행계획서 입력 ", padding=15)
        paned.add(input_frame, weight=1)

        # 입력 필드들
        row = 0

        # 콜사인
        ttk.Label(input_frame, text="콜사인 (Callsign)*").grid(row=row, column=0, sticky=W, pady=5)
        self.callsign_var = StringVar()
        ttk.Entry(input_frame, textvariable=self.callsign_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 기종
        ttk.Label(input_frame, text="기종 (ICAO)").grid(row=row, column=0, sticky=W, pady=5)
        self.aircraft_var = StringVar()
        ttk.Entry(input_frame, textvariable=self.aircraft_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 속도
        ttk.Label(input_frame, text="속도 (Speed)").grid(row=row, column=0, sticky=W, pady=5)
        self.speed_var = StringVar(value="K0850")
        ttk.Entry(input_frame, textvariable=self.speed_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 고도
        ttk.Label(input_frame, text="고도 (Level)").grid(row=row, column=0, sticky=W, pady=5)
        self.altitude_var = StringVar(value="370")
        ttk.Entry(input_frame, textvariable=self.altitude_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 출발지
        ttk.Label(input_frame, text="출발지 (Dept)*").grid(row=row, column=0, sticky=W, pady=5)
        self.dept_var = StringVar()
        ttk.Entry(input_frame, textvariable=self.dept_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 도착지
        ttk.Label(input_frame, text="도착지 (Dest)*").grid(row=row, column=0, sticky=W, pady=5)
        self.dest_var = StringVar()
        ttk.Entry(input_frame, textvariable=self.dest_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 날짜
        ttk.Label(input_frame, text="비행날짜 (EOBD)").grid(row=row, column=0, sticky=W, pady=5)
        self.eobd_var = StringVar(value=date.today().strftime("%Y-%m-%d"))
        ttk.Entry(input_frame, textvariable=self.eobd_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 출발시간
        ttk.Label(input_frame, text="출발시간 (EOBT)").grid(row=row, column=0, sticky=W, pady=5)
        self.eobt_var = StringVar(value="00:00")
        ttk.Entry(input_frame, textvariable=self.eobt_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # EET
        ttk.Label(input_frame, text="EET").grid(row=row, column=0, sticky=W, pady=5)
        self.eet_var = StringVar()
        ttk.Entry(input_frame, textvariable=self.eet_var, width=20).grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 항로
        ttk.Label(input_frame, text="항로 (Route)*").grid(row=row, column=0, sticky=NW, pady=5)
        self.route_text = Text(input_frame, width=35, height=4, wrap=WORD)
        self.route_text.grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # 버튼 프레임
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="계산하기", command=self.calculate).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="초기화", command=self.clear_inputs).pack(side=LEFT, padx=5)

        # === 오른쪽: 결과 표시 ===
        result_frame = ttk.Frame(paned)
        paned.add(result_frame, weight=2)

        # 확장 경로
        route_exp_frame = ttk.LabelFrame(result_frame, text=" 확장 경로 ", padding=10)
        route_exp_frame.pack(fill=X, pady=(0, 10))

        self.route_expansion_var = StringVar(value="계산 결과가 여기에 표시됩니다.")
        ttk.Label(route_exp_frame, textvariable=self.route_expansion_var, wraplength=600).pack(fill=X)

        # 섹터 테이블
        sector_frame = ttk.LabelFrame(result_frame, text=" 섹터 통과 정보 ", padding=10)
        sector_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        sector_scroll = ttk.Scrollbar(sector_frame, orient=VERTICAL)
        self.sector_tree = ttk.Treeview(
            sector_frame,
            columns=("sector", "entry", "exit", "duration"),
            show="headings",
            yscrollcommand=sector_scroll.set,
            height=6
        )
        sector_scroll.config(command=self.sector_tree.yview)

        self.sector_tree.heading("sector", text="섹터명")
        self.sector_tree.heading("entry", text="진입 시간")
        self.sector_tree.heading("exit", text="진출 시간")
        self.sector_tree.heading("duration", text="체류 시간(분)")

        self.sector_tree.column("sector", width=100)
        self.sector_tree.column("entry", width=100)
        self.sector_tree.column("exit", width=100)
        self.sector_tree.column("duration", width=100)

        self.sector_tree.pack(side=LEFT, fill=BOTH, expand=True)
        sector_scroll.pack(side=RIGHT, fill=Y)

        # 웨이포인트 테이블
        wp_frame = ttk.LabelFrame(result_frame, text=" 지점별 통과 시간 ", padding=10)
        wp_frame.pack(fill=BOTH, expand=True)

        wp_scroll = ttk.Scrollbar(wp_frame, orient=VERTICAL)
        self.wp_tree = ttk.Treeview(
            wp_frame,
            columns=("no", "name", "time", "coords"),
            show="headings",
            yscrollcommand=wp_scroll.set,
            height=10
        )
        wp_scroll.config(command=self.wp_tree.yview)

        self.wp_tree.heading("no", text="순번")
        self.wp_tree.heading("name", text="지점명")
        self.wp_tree.heading("time", text="통과 시간")
        self.wp_tree.heading("coords", text="좌표 (Lat, Lon)")

        self.wp_tree.column("no", width=50)
        self.wp_tree.column("name", width=100)
        self.wp_tree.column("time", width=100)
        self.wp_tree.column("coords", width=180)

        self.wp_tree.pack(side=LEFT, fill=BOTH, expand=True)
        wp_scroll.pack(side=RIGHT, fill=Y)

    def create_fix_times_tab(self):
        """FIX 이동시간 관리 탭 UI"""
        # 상단 툴바
        toolbar = ttk.Frame(self.fix_times_frame, padding=10)
        toolbar.pack(fill=X)

        ttk.Button(toolbar, text="TXT 업로드", command=self.upload_fix_times_txt).pack(side=LEFT, padx=5)

        # 집계 방법 선택
        ttk.Label(toolbar, text="집계방법:").pack(side=LEFT, padx=(20, 5))
        self.method_var = StringVar(value="average")
        method_combo = ttk.Combobox(toolbar, textvariable=self.method_var, width=10, state="readonly")
        method_combo['values'] = ("average", "median", "min", "max")
        method_combo.pack(side=LEFT)

        ttk.Button(toolbar, text="새로고침", command=self.load_fix_times).pack(side=LEFT, padx=20)
        ttk.Button(toolbar, text="JSON 저장", command=self.save_fix_times).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="추가", command=self.add_fix_time_dialog).pack(side=LEFT, padx=5)

        # 검색
        ttk.Label(toolbar, text="검색:").pack(side=LEFT, padx=(30, 5))
        self.search_var = StringVar()
        self.search_var.trace('w', lambda *args: self.filter_fix_times())
        ttk.Entry(toolbar, textvariable=self.search_var, width=15).pack(side=LEFT)

        # 개수 표시
        self.count_var = StringVar(value="총 0개")
        ttk.Label(toolbar, textvariable=self.count_var).pack(side=RIGHT, padx=10)

        # 상태 표시
        self.status_var = StringVar()
        self.status_label = ttk.Label(self.fix_times_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(fill=X, padx=10)

        # 테이블
        table_frame = ttk.Frame(self.fix_times_frame, padding=10)
        table_frame.pack(fill=BOTH, expand=True)

        # 스크롤바
        y_scroll = ttk.Scrollbar(table_frame, orient=VERTICAL)
        x_scroll = ttk.Scrollbar(table_frame, orient=HORIZONTAL)

        self.fix_tree = ttk.Treeview(
            table_frame,
            columns=("from", "to", "time"),
            show="headings",
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        y_scroll.config(command=self.fix_tree.yview)
        x_scroll.config(command=self.fix_tree.xview)

        self.fix_tree.heading("from", text="출발 FIX")
        self.fix_tree.heading("to", text="도착 FIX")
        self.fix_tree.heading("time", text="이동시간 (분)")

        self.fix_tree.column("from", width=150)
        self.fix_tree.column("to", width=150)
        self.fix_tree.column("time", width=120)

        self.fix_tree.pack(side=LEFT, fill=BOTH, expand=True)
        y_scroll.pack(side=RIGHT, fill=Y)
        x_scroll.pack(side=BOTTOM, fill=X)

        # 더블클릭 편집
        self.fix_tree.bind('<Double-1>', self.edit_fix_time)

        # 삭제 버튼
        delete_frame = ttk.Frame(self.fix_times_frame, padding=10)
        delete_frame.pack(fill=X)
        ttk.Button(delete_frame, text="선택 항목 삭제", command=self.delete_fix_time).pack(side=RIGHT)

        # 초기 로드
        self.load_fix_times()

    def load_resources(self):
        """리소스 로드"""
        try:
            self.status_var.set("리소스를 로드하는 중...")
            self.root.update()

            # 데이터베이스 경로
            db_path = os.path.join(PROJECT_DIR, 'database', 'similarity_detector.db')
            if not os.path.exists(db_path):
                messagebox.showerror("오류", f"데이터베이스 파일을 찾을 수 없습니다:\n{db_path}")
                return

            self.db_manager = DatabaseManager(db_path)
            self.resources = get_modeling_resources()

            self.status_var.set("리소스 로드 완료")

        except Exception as e:
            messagebox.showerror("오류", f"리소스 로드 실패:\n{str(e)}")
            self.status_var.set(f"오류: {str(e)}")

    def calculate(self):
        """모델링 계산 실행"""
        # 입력 검증
        callsign = self.callsign_var.get().strip()
        dept = self.dept_var.get().strip().upper()
        dest = self.dest_var.get().strip().upper()
        route = self.route_text.get("1.0", END).strip()

        if not callsign:
            messagebox.showwarning("입력 오류", "콜사인을 입력하세요.")
            return
        if not dept:
            messagebox.showwarning("입력 오류", "출발지를 입력하세요.")
            return
        if not dest:
            messagebox.showwarning("입력 오류", "도착지를 입력하세요.")
            return
        if not route:
            messagebox.showwarning("입력 오류", "항로를 입력하세요.")
            return

        if not self.resources:
            messagebox.showerror("오류", "리소스가 로드되지 않았습니다.")
            return

        try:
            # 비행 데이터 구성
            flight_data = {
                'callsign': callsign,
                'aircraft_type': self.aircraft_var.get().strip().upper(),
                'speed': self.speed_var.get().strip(),
                'altitude': self.altitude_var.get().strip(),
                'dept': dept,
                'dest': dest,
                'eobd': self.eobd_var.get().strip(),
                'eobt': self.eobt_var.get().strip(),
                'route': route,
                'eet': self.eet_var.get().strip(),
                'info_cn': ''
            }

            # 항공기 프로필 조회
            if flight_data['aircraft_type']:
                profile = self.db_manager.get_aircraft_profile(flight_data['aircraft_type'])
                if profile:
                    flight_data['aircraft_profile'] = profile

            # 계산 실행
            result = calculate_trajectory(
                flight_data,
                self.resources['coord_map'],
                self.resources['sectors'],
                self.resources['enroute_df'],
                self.resources['fix_col']
            )

            if result.get('status') == 'success':
                self.display_results(result)
            else:
                messagebox.showerror("계산 오류", result.get('message', '알 수 없는 오류'))

        except Exception as e:
            messagebox.showerror("오류", f"계산 중 오류 발생:\n{str(e)}")

    def display_results(self, result):
        """결과 표시"""
        # 확장 경로
        self.route_expansion_var.set(result.get('route_expansion', '-'))

        # 섹터 테이블 초기화
        for item in self.sector_tree.get_children():
            self.sector_tree.delete(item)

        sectors = result.get('sectors', [])
        for s in sectors:
            duration = self.calc_duration(s.get('entry', ''), s.get('exit', ''))
            self.sector_tree.insert('', END, values=(
                s.get('name', '-'),
                s.get('entry', '-'),
                s.get('exit', '-'),
                duration
            ))

        # 웨이포인트 테이블 초기화
        for item in self.wp_tree.get_children():
            self.wp_tree.delete(item)

        waypoints = result.get('waypoints', [])
        for i, wp in enumerate(waypoints, 1):
            lat = wp.get('lat', 0)
            lon = wp.get('lon', 0)
            self.wp_tree.insert('', END, values=(
                i,
                wp.get('name', '-'),
                wp.get('time', '-'),
                f"{lat:.4f}, {lon:.4f}"
            ))

    def calc_duration(self, entry, exit_time):
        """체류시간 계산 (분)"""
        try:
            h1, m1 = map(int, entry.split(':'))
            h2, m2 = map(int, exit_time.split(':'))
            diff = (h2 * 60 + m2) - (h1 * 60 + m1)
            if diff < 0:
                diff += 24 * 60
            return diff
        except:
            return '-'

    def clear_inputs(self):
        """입력 초기화"""
        self.callsign_var.set('')
        self.aircraft_var.set('')
        self.speed_var.set('K0850')
        self.altitude_var.set('370')
        self.dept_var.set('')
        self.dest_var.set('')
        self.eobd_var.set(date.today().strftime("%Y-%m-%d"))
        self.eobt_var.set('00:00')
        self.eet_var.set('')
        self.route_text.delete("1.0", END)

        # 결과 초기화
        self.route_expansion_var.set("계산 결과가 여기에 표시됩니다.")
        for item in self.sector_tree.get_children():
            self.sector_tree.delete(item)
        for item in self.wp_tree.get_children():
            self.wp_tree.delete(item)

    # ========== FIX 이동시간 관리 메서드 ==========

    def load_fix_times(self):
        """FIX 이동시간 데이터 로드"""
        try:
            json_path = os.path.join(PROJECT_DIR, 'database', 'fix_travel_times_lookup.json')

            if not os.path.exists(json_path):
                self.status_var.set("JSON 파일이 없습니다.")
                self.fix_times_data = []
                return

            data = load_json_file(json_path)
            if data:
                self.fix_times_data = flatten_fix_times(data)
                self.filter_fix_times()
                self.status_var.set(f"로드 완료: {len(self.fix_times_data)}개")
            else:
                self.fix_times_data = []
                self.status_var.set("데이터 없음")

        except Exception as e:
            self.status_var.set(f"로드 오류: {str(e)}")
            messagebox.showerror("오류", f"FIX 이동시간 로드 실패:\n{str(e)}")

    def filter_fix_times(self):
        """검색 필터 적용"""
        query = self.search_var.get().upper().strip()

        # 테이블 초기화
        for item in self.fix_tree.get_children():
            self.fix_tree.delete(item)

        filtered = self.fix_times_data
        if query:
            filtered = [d for d in self.fix_times_data
                       if query in d['from_fix'] or query in d['to_fix']]

        for item in filtered:
            self.fix_tree.insert('', END, values=(
                item['from_fix'],
                item['to_fix'],
                item['time_minutes']
            ))

        self.count_var.set(f"총 {len(filtered)}개")

    def upload_fix_times_txt(self):
        """TXT 파일 업로드 및 변환"""
        file_path = filedialog.askopenfilename(
            title="fixtime.txt 파일 선택",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            method = self.method_var.get()

            # 변환
            json_data = convert_fixtime_to_json(content, method)
            stats = get_conversion_statistics(content)

            # 저장
            json_path = os.path.join(PROJECT_DIR, 'database', 'fix_travel_times_lookup.json')
            if save_json_file(json_data, json_path):
                # 캐시 갱신
                _reload_fix_travel_lookup()

                # 리로드
                self.load_fix_times()

                msg = f"변환 완료!\n\n"
                msg += f"처리된 라인: {stats['total_lines']}개\n"
                msg += f"FIX 쌍: {stats['total_fix_pairs']}개\n"
                msg += f"총 샘플: {stats['total_samples']}개\n"
                msg += f"고유 FIX: {stats['unique_fixes']}개"

                messagebox.showinfo("성공", msg)
            else:
                messagebox.showerror("오류", "JSON 파일 저장 실패")

        except Exception as e:
            messagebox.showerror("오류", f"파일 처리 오류:\n{str(e)}")

    def save_fix_times(self):
        """현재 데이터 JSON 저장"""
        try:
            json_path = os.path.join(PROJECT_DIR, 'database', 'fix_travel_times_lookup.json')

            # 플랫 리스트 → 중첩 딕셔너리
            data = {}
            for item in self.fix_times_data:
                from_fix = item['from_fix']
                to_fix = item['to_fix']
                time_min = item['time_minutes']

                if from_fix not in data:
                    data[from_fix] = {}
                data[from_fix][to_fix] = time_min

            if save_json_file(data, json_path):
                _reload_fix_travel_lookup()
                self.status_var.set("저장 완료")
                messagebox.showinfo("성공", "JSON 파일 저장 완료")
            else:
                messagebox.showerror("오류", "저장 실패")

        except Exception as e:
            messagebox.showerror("오류", f"저장 오류:\n{str(e)}")

    def add_fix_time_dialog(self):
        """FIX 이동시간 추가 다이얼로그"""
        dialog = FixTimeDialog(self.root, "FIX 이동시간 추가")
        if dialog.result:
            from_fix = dialog.result['from_fix'].upper()
            to_fix = dialog.result['to_fix'].upper()
            time_min = dialog.result['time_minutes']

            # 중복 체크
            existing = [d for d in self.fix_times_data
                       if d['from_fix'] == from_fix and d['to_fix'] == to_fix]
            if existing:
                existing[0]['time_minutes'] = time_min
            else:
                self.fix_times_data.append({
                    'from_fix': from_fix,
                    'to_fix': to_fix,
                    'time_minutes': time_min
                })

            self.filter_fix_times()
            self.status_var.set(f"추가됨: {from_fix} → {to_fix}")

    def edit_fix_time(self, event):
        """더블클릭으로 편집"""
        selection = self.fix_tree.selection()
        if not selection:
            return

        item = self.fix_tree.item(selection[0])
        values = item['values']

        dialog = FixTimeDialog(
            self.root,
            "FIX 이동시간 수정",
            from_fix=values[0],
            to_fix=values[1],
            time_minutes=values[2]
        )

        if dialog.result:
            # 데이터 업데이트
            for d in self.fix_times_data:
                if d['from_fix'] == values[0] and d['to_fix'] == values[1]:
                    d['time_minutes'] = dialog.result['time_minutes']
                    break

            self.filter_fix_times()
            self.status_var.set(f"수정됨: {values[0]} → {values[1]}")

    def delete_fix_time(self):
        """선택 항목 삭제"""
        selection = self.fix_tree.selection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 항목을 선택하세요.")
            return

        if not messagebox.askyesno("확인", "선택한 항목을 삭제하시겠습니까?"):
            return

        for sel in selection:
            item = self.fix_tree.item(sel)
            values = item['values']

            self.fix_times_data = [
                d for d in self.fix_times_data
                if not (d['from_fix'] == values[0] and d['to_fix'] == values[1])
            ]

        self.filter_fix_times()
        self.status_var.set("삭제 완료")


class FixTimeDialog:
    """FIX 이동시간 입력 다이얼로그"""

    def __init__(self, parent, title, from_fix='', to_fix='', time_minutes=''):
        self.result = None

        self.dialog = Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("300x200")
        self.dialog.grab_set()

        # 입력 필드
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="출발 FIX:").grid(row=0, column=0, sticky=W, pady=5)
        self.from_entry = ttk.Entry(frame, width=20)
        self.from_entry.insert(0, from_fix)
        self.from_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="도착 FIX:").grid(row=1, column=0, sticky=W, pady=5)
        self.to_entry = ttk.Entry(frame, width=20)
        self.to_entry.insert(0, to_fix)
        self.to_entry.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="이동시간 (분):").grid(row=2, column=0, sticky=W, pady=5)
        self.time_entry = ttk.Entry(frame, width=20)
        self.time_entry.insert(0, str(time_minutes))
        self.time_entry.grid(row=2, column=1, pady=5)

        # 수정 모드일 때 FIX 필드 비활성화
        if from_fix and to_fix:
            self.from_entry.config(state=DISABLED)
            self.to_entry.config(state=DISABLED)

        # 버튼
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="저장", command=self.save).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="취소", command=self.cancel).pack(side=LEFT, padx=5)

        self.dialog.wait_window()

    def save(self):
        from_fix = self.from_entry.get().strip()
        to_fix = self.to_entry.get().strip()
        time_str = self.time_entry.get().strip()

        if not from_fix or not to_fix:
            messagebox.showwarning("경고", "출발/도착 FIX를 입력하세요.")
            return

        try:
            time_min = float(time_str)
            if time_min < 0:
                raise ValueError()
        except:
            messagebox.showwarning("경고", "유효한 시간 값을 입력하세요.")
            return

        self.result = {
            'from_fix': from_fix.upper(),
            'to_fix': to_fix.upper(),
            'time_minutes': round(time_min, 1)
        }
        self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


def main():
    """메인 실행"""
    root = Tk()
    app = ModelingTestGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
