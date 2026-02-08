let nutritionChart;
let growthChart;
let currentViewDate = new Date();

document.addEventListener('DOMContentLoaded', function () {
    console.log("유나의 식단 일기 앱 시작!");

    initChart();
    initGrowthChart(); // 성장 차트 초기화
    loadUserData();
    loadDashboard();
    loadRecommendation();
    renderCalendar();
    loadGrowthData(); // 성장 데이터 로드
    setDefaultMealType(); // 현재 시간 기준 기본 식사 시간 설정

    // 시간대별 기본 식사 시간 자동 설정
    function setDefaultMealType() {
        const mealTypeSelect = document.getElementById('mealType');
        if (!mealTypeSelect) return;

        const hour = new Date().getHours();
        let defaultType = '간식';

        if (hour >= 5 && hour < 11) {
            defaultType = '아침';
        } else if (hour >= 11 && hour < 15) {
            defaultType = '점심';
        } else if (hour >= 15 && hour < 17) {
            defaultType = '간식';
        } else if (hour >= 17 && hour < 21) {
            defaultType = '저녁';
        } else {
            defaultType = '간식';
        }

        mealTypeSelect.value = defaultType;
    }

    // 프로필 저장 핸들러
    const saveProfileBtn = document.getElementById('saveProfileBtn');
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener('click', function () {
            const months = document.getElementById('user-months').value;
            fetch('/api/user/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ months: months })
            })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    loadDashboard();
                    loadRecommendation();
                    renderCalendar();
                });
        });
    }

    // 식단 기록 폼 제출 핸들러
    const mealForm = document.getElementById('mealForm');
    if (mealForm) {
        mealForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(mealForm);
            const mealData = {
                mealType: formData.get('mealType'),
                amount: formData.get('amount'),
                menuName: formData.get('menuName'),
                calories: parseFloat(formData.get('calories')) || 0,
                carbs: parseFloat(formData.get('carbs')) || 0,
                protein: parseFloat(formData.get('protein')) || 0,
                fat: parseFloat(formData.get('fat')) || 0
            };

            fetch('/api/record', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mealData)
            })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    mealForm.reset();
                    setDefaultMealType(); // 기록 후에도 현재 시간 맞춰 재생성
                    loadDashboard(); // 대시보드 새로고침
                    loadRecommendation(); // 추천 새로고침
                    renderCalendar();
                });
        });
    }

    // 캘린더 이동 제어
    document.getElementById('prevMonth').addEventListener('click', () => {
        currentViewDate.setMonth(currentViewDate.getMonth() - 1);
        renderCalendar();
    });
    document.getElementById('nextMonth').addEventListener('click', () => {
        currentViewDate.setMonth(currentViewDate.getMonth() + 1);
        renderCalendar();
    });

    // TTS 버튼
    const speakBtn = document.getElementById('speakBtn');
    if (speakBtn) {
        speakBtn.addEventListener('click', function () {
            const textToSpeak = document.querySelector('#recommendation-content').innerText;
            speak(textToSpeak);
        });
    }

    // 성장 기록 폼 제출 핸들러
    const growthForm = document.getElementById('growthForm');
    if (growthForm) {
        growthForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(growthForm);
            const months = document.getElementById('user-months').value;
            const growthData = {
                height: formData.get('height'),
                weight: formData.get('weight'),
                months: months
            };

            fetch('/api/growth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(growthData)
            })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    const statusEl = document.getElementById('growth-status');
                    if (statusEl) statusEl.innerText = data.message;
                    growthForm.reset();
                    loadGrowthData();
                });
        });
    }

    // 성장 일기 토글 핸들러
    const toggleGrowthBtn = document.getElementById('toggle-growth');
    if (toggleGrowthBtn) {
        toggleGrowthBtn.addEventListener('click', function () {
            const wrapper = document.getElementById('growth-content-wrapper');
            const icon = document.getElementById('growth-toggle-icon');
            wrapper.classList.toggle('collapsed');

            if (wrapper.classList.contains('collapsed')) {
                icon.style.transform = 'rotate(0deg)';
            } else {
                icon.style.transform = 'rotate(180deg)';
            }
        });
    }

    // 성장 기록 목록 토글 핸들러
    const toggleGrowthHistoryBtn = document.getElementById('toggle-growth-history');
    if (toggleGrowthHistoryBtn) {
        toggleGrowthHistoryBtn.addEventListener('click', function () {
            const listContainer = document.getElementById('growth-history-list');
            const isHidden = listContainer.style.display === 'none';
            listContainer.style.display = isHidden ? 'block' : 'none';
            this.innerText = isHidden ? '관리 모드 닫기' : '성장 기록 현황 보러가기';
            this.style.backgroundColor = isHidden ? '#ff7675' : '#74b9ff';
        });
    }

    // 건강 스케줄 전체보기 토글 핸들러
    const toggleFullScheduleBtn = document.getElementById('toggle-full-schedule');
    if (toggleFullScheduleBtn) {
        toggleFullScheduleBtn.addEventListener('click', function () {
            const fullSchedule = document.getElementById('full-health-schedule');
            fullSchedule.classList.toggle('collapsed');
            this.innerText = fullSchedule.classList.contains('collapsed') ? '전체 일정 보기' : '일정 닫기';
            this.style.backgroundColor = fullSchedule.classList.contains('collapsed') ? 'var(--secondary-color)' : '#ff7675';
        });
    }
});

function deleteGrowthRecord(id) {
    if (!confirm("이 성장 기록을 삭제하시겠습니까?")) return;

    fetch('/api/growth/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id })
    })
        .then(res => res.json())
        .then(data => {
            alert(data.message);
            loadGrowthData();
        });
}

function initChart() {
    const ctx = document.getElementById('nutritionChart').getContext('2d');
    nutritionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['탄수화물', '단백질', '지방'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#FF9F43', '#54A0FF', '#1DD1A1'],
                borderWidth: 5,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: "'Jua', sans-serif", size: 14 } }
                }
            },
            cutout: '70%'
        }
    });
}

function loadDashboard() {
    fetch('/api/data')
        .then(res => res.json())
        .then(data => {
            const meals = data.meals || [];
            if (data.user && data.user.target_nutrition) {
                document.getElementById('target-calories-display').innerText = `권장 칼로리: ${data.user.target_nutrition.calories} kcal`;
            }

            // 로컬 날짜 기준으로 오늘 날짜 필터링 (ISO는 UTC 기준이라 시차 문제 발생 가능)
            const now = new Date();
            const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
            const todayMeals = meals.filter(m => m.date.startsWith(today));

            // 영양소 합계 계산
            let totals = { carbs: 0, protein: 0, fat: 0, calories: 0 };
            const mealList = document.getElementById('meal-list');
            mealList.innerHTML = '';

            if (todayMeals.length === 0) {
                mealList.innerHTML = '<p class="empty-msg">아직 기록이 없어요.</p>';
            } else {
                todayMeals.forEach(meal => {
                    totals.carbs += meal.carbs;
                    totals.protein += meal.protein;
                    totals.fat += meal.fat;
                    totals.calories += meal.calories;

                    // 식사 유형 및 메뉴 이름 안전하게 가져오기
                    const mealType = meal.meal_type || meal.mealType || '간식';
                    const menuName = meal.menu_name || meal.menuName || '기록 없음';

                    // 식사 유형별 클래스 매핑
                    const typeClassMap = { '아침': 'breakfast', '점심': 'lunch', '저녁': 'dinner', '간식': 'snack' };
                    const typeClass = typeClassMap[mealType] || '';

                    const item = document.createElement('div');
                    item.className = `meal-item ${typeClass}`;
                    item.innerHTML = `
                        <div class="info">
                            <span class="menu">${menuName} <small style="color: #888; font-weight: normal;">(${meal.amount || '보통'})</small></span>
                            <span class="specs">칼로리: ${meal.calories}kcal | 탄: ${meal.carbs}g 단: ${meal.protein}g 지: ${meal.fat}g</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span class="type ${typeClass}">${mealType}</span>
                            <button class="delete-btn" onclick="deleteMeal('${meal.id}')" title="삭제">×</button>
                        </div>
                    `;
                    mealList.appendChild(item);
                });
            }

            // 차트 업데이트
            nutritionChart.data.datasets[0].data = [totals.carbs, totals.protein, totals.fat];
            nutritionChart.update();
        });
}

function deleteMeal(id) {
    if (!id) {
        alert("삭제할 수 없는 항목입니다 (ID 누락).");
        return;
    }
    if (confirm("이 기록을 삭제할까요?")) {
        fetch('/api/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        })
            .then(res => res.json())
            .then(data => {
                loadDashboard();
                loadRecommendation();
                renderCalendar();
            });
    }
}

function loadRecommendation() {
    const recContent = document.getElementById('recommendation-content');
    fetch('/api/recommend')
        .then(res => res.json())
        .then(data => {
            const rec = data.recommendation;
            recContent.innerHTML = `
            <p style="color: #666; font-size: 0.9rem; margin-bottom: 15px;">📊 <strong>주간 분석:</strong> ${data.tendency}</p>
            <h3 style="margin-bottom: 10px; color: var(--primary-color);">✨ 유나를 위한 맞춤 하루 식단 (${data.months}개월/${data.stage_name})</h3>
            <div class="rec-grid">
                <div class="rec-item"><span class="label">☀️ 아침</span><span class="menu">${rec.breakfast}</span></div>
                <div class="rec-item"><span class="label">🌤️ 점심</span><span class="menu">${rec.lunch}</span></div>
                <div class="rec-item"><span class="label">🌙 저녁</span><span class="menu">${rec.dinner}</span></div>
                <div class="rec-item"><span class="label">🍎 간식</span><span class="menu">${rec.snack}</span></div>
            </div>
            <div class="rec-tip">💡 <strong>성장 팁:</strong> ${data.tip}</div>
        `;
        });
}

function renderCalendar() {
    const year = currentViewDate.getFullYear();
    const month = currentViewDate.getMonth();

    document.getElementById('currentMonthYear').innerText = `${year}년 ${month + 1}월`;

    const firstDay = new Date(year, month, 1).getDay();
    const lastDate = new Date(year, month + 1, 0).getDate();
    const calendarBody = document.getElementById('calendar-body');
    calendarBody.innerHTML = '';

    // 서버에서 데이터 가져와 매칭
    fetch('/api/data')
        .then(res => res.json())
        .then(data => {
            const meals = data.meals || [];

            // 빈칸 (이전 달 끝부분)
            for (let i = 0; i < firstDay; i++) {
                const emptyCell = document.createElement('div');
                calendarBody.appendChild(emptyCell);
            }

            // 날짜 채우기
            const today = new Date();
            for (let d = 1; d <= lastDate; d++) {
                const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
                const dayMeals = meals.filter(m => m.date.startsWith(dateStr));

                const cell = document.createElement('div');
                cell.className = 'calendar-day';
                if (year === today.getFullYear() && month === today.getMonth() && d === today.getDate()) {
                    cell.classList.add('today');
                }

                cell.innerHTML = `<span class="day-num">${d}</span>`;

                if (dayMeals.length > 0) {
                    const labelsContainer = document.createElement('div');
                    labelsContainer.className = 'meal-labels';

                    // 식사 타입별로 그룹화하여 표시
                    const mealTypes = ['아침', '점심', '저녁', '간식'];
                    mealTypes.forEach(type => {
                        const mealsOfType = dayMeals.filter(m => {
                            const mType = m.meal_type || m.mealType || '';
                            return mType.includes(type);
                        });
                        if (mealsOfType.length > 0) {
                            const label = document.createElement('div');
                            label.className = `meal-label ${getTypeClass(type)}`;
                            const menuNames = mealsOfType.map(m => m.menu_name || m.menuName || '기록 없음').join(', ');
                            label.innerText = `${type}: ${menuNames}`;
                            label.title = menuNames; // 툴팁으로 전체 메뉴 확인 가능
                            labelsContainer.appendChild(label);
                        }
                    });
                    cell.appendChild(labelsContainer);
                }

                calendarBody.appendChild(cell);
            }
        });
}

function getTypeClass(type) {
    if (type.includes('아침')) return 'breakfast';
    if (type.includes('점심')) return 'lunch';
    if (type.includes('저녁')) return 'dinner';
    return 'snack';
}

function loadUserData() {
    fetch('/api/data')
        .then(res => res.json())
        .then(data => {
            if (data.user) {
                document.getElementById('user-months').value = data.user.months;
                if (data.user.target_nutrition) {
                    document.getElementById('target-calories-display').innerText = `권장 칼로리: ${data.user.target_nutrition.calories} kcal`;
                }

                // 디데이 및 상세 연령(개월/일) 계산 및 표시
                if (data.user.birth_date) {
                    const birthDate = new Date(data.user.birth_date);
                    const today = new Date();

                    // 1. D-Day 계산
                    const birthDateForDDay = new Date(data.user.birth_date);
                    birthDateForDDay.setHours(0, 0, 0, 0);
                    const todayForDDay = new Date();
                    todayForDDay.setHours(0, 0, 0, 0);
                    const diffTime = Math.abs(todayForDDay - birthDateForDDay);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
                    document.getElementById('d-day-display').innerText = `D+${diffDays}`;

                    // 2. 개월/일 계산 (X개월 Y일)
                    let years = today.getFullYear() - birthDate.getFullYear();
                    let months = today.getMonth() - birthDate.getMonth();
                    let days = today.getDate() - birthDate.getDate();

                    if (days < 0) {
                        months -= 1;
                        const lastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
                        days += lastMonth.getDate();
                    }
                    if (months < 0) {
                        years -= 1;
                        months += 12;
                    }

                    const totalMonths = (years * 12) + months;
                    document.getElementById('age-display').innerText = `(${totalMonths}개월 ${days}일)`;

                    // 숨겨진 입력필드 업데이트 (영양 분석용)
                    document.getElementById('user-months').value = totalMonths;

                    // 건강 스케줄 렌더링
                    renderHealthSchedule(data.user.birth_date);
                }

                // 취향 데이터 렌더링
                renderTags('likes-tags', data.user.likes || [], 'like');
                renderTags('dislikes-tags', data.user.dislikes || [], 'dislike');
            }
        });
}

function renderTags(containerId, list, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    list.forEach(item => {
        const tag = document.createElement('span');
        tag.className = `tag ${type}`;
        tag.innerHTML = `${item} <span class="remove-tag" onclick="removePreference('${item}', '${type}')">×</span>`;
        container.appendChild(tag);
    });
}

function handlePrefInput(e, type) {
    if (e.key === 'Enter' && e.target.value.trim() !== '') {
        const value = e.target.value.trim();
        fetch('/api/data')
            .then(res => res.json())
            .then(data => {
                let likes = data.user.likes || [];
                let dislikes = data.user.dislikes || [];

                if (type === 'like') {
                    if (!likes.includes(value)) likes.push(value);
                } else {
                    if (!dislikes.includes(value)) dislikes.push(value);
                }

                savePreferences(likes, dislikes);
                e.target.value = '';
            });
    }
}

function removePreference(value, type) {
    fetch('/api/data')
        .then(res => res.json())
        .then(data => {
            let likes = data.user.likes || [];
            let dislikes = data.user.dislikes || [];
            if (type === 'like') {
                likes = likes.filter(i => i !== value);
            } else {
                dislikes = dislikes.filter(i => i !== value);
            }
            savePreferences(likes, dislikes);
        });
}

function savePreferences(likes, dislikes) {
    fetch('/api/user/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ likes, dislikes })
    })
        .then(res => res.json())
        .then(() => {
            loadUserData();
            loadRecommendation(); // 추천 즉시 갱신
        });
}

// 이벤트 리스너 추가 (DOMContentLoaded 내부에 추가될 수 있도록 helper 호출 등의 구조 고려)
document.addEventListener('keydown', function (e) {
    if (e.target.id === 'like-input') handlePrefInput(e, 'like');
    if (e.target.id === 'dislike-input') handlePrefInput(e, 'dislike');
});

// 성장 차트 초기화
function initGrowthChart() {
    const ctxElement = document.getElementById('growthChart');
    if (!ctxElement) return;
    const ctx = ctxElement.getContext('2d');
    growthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '키 (cm)',
                    data: [],
                    borderColor: '#9c88ff',
                    backgroundColor: '#9c88ff44',
                    yAxisID: 'yH',
                    tension: 0.3,
                    fill: true
                },
                {
                    label: '몸무게 (kg)',
                    data: [],
                    borderColor: '#ff9f43',
                    backgroundColor: '#ff9f4344',
                    yAxisID: 'yW',
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                yH: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: '키 (cm)' }
                },
                yW: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: '몸무게 (kg)', font: { size: 12 } },
                    grid: { drawOnChartArea: false }
                }
            },
            plugins: {
                legend: { position: 'top' }
            }
        }
    });
}

// 성장 데이터 로드 및 렌더링
function loadGrowthData() {
    fetch('/api/growth/history')
        .then(res => res.json())
        .then(data => {
            const history = data.history || [];

            // 성장 기록 현황 목록 렌더링
            const historyList = document.getElementById('growth-history-list');
            if (historyList) {
                if (history.length === 0) {
                    historyList.innerHTML = '<p style="text-align: center; color: #888;">아직 기록된 성장 데이터가 없습니다.</p>';
                } else {
                    // 최신순으로 표시하기 위해 배열 복사 후 reverse
                    const sortedHistory = [...history].reverse();
                    historyList.innerHTML = sortedHistory.map(h => `
                        <div class="growth-history-item">
                            <span class="date">${h.date.split(' ')[0]}</span>
                            <span class="info">🦒 ${h.height}cm | ⚖️ ${h.weight}kg</span>
                            <span class="actions">
                                <button class="delete-btn" onclick="deleteGrowthRecord('${h.id}')" title="삭제" style="background: none; border: none; color: #ff7675; cursor: pointer; font-size: 1.2rem;">×</button>
                            </span>
                        </div>
                    `).join('');
                }
            }

            if (history.length === 0) return;

            const labels = history.map(h => h.date.split(' ')[0]);
            const heights = history.map(h => h.height);
            const weights = history.map(h => h.weight);

            if (growthChart) {
                growthChart.data.labels = labels;
                growthChart.data.datasets[0].data = heights;
                growthChart.data.datasets[1].data = weights;
                growthChart.update();
            }

            // 마지막 기록으로 상태 메시지 업데이트
            const last = history[history.length - 1];
            const statusEl = document.getElementById('growth-status');
            if (statusEl) {
                statusEl.innerText = `마지막 기록(${last.months}개월): 키 백분위 ${last.h_percentile} (상위 ${Math.round((100 - last.h_percentile) * 10) / 10}%) | 몸무게 백분위 ${last.w_percentile} (상위 ${Math.round((100 - last.w_percentile) * 10) / 10}%)`;
            }
        });
}

function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // 이전 음성 취소

        // 한글, 영어, 숫자, 공백만 남기고 모든 기호(이모지 등) 제거
        const cleanedText = text.replace(/[^가-힣a-zA-Z0-9\s]/g, "");

        const utterance = new SpeechSynthesisUtterance(cleanedText);
        utterance.lang = 'ko-KR';
        utterance.rate = 1.0;
        utterance.pitch = 1.2;
        window.speechSynthesis.speak(utterance);
    }
}

// 건강 스케줄 데이터 및 렌더링 로직
const HEALTH_SCHEDULE = [
    { type: '검진', title: '영유아 건강검진 (1차)', start: 14, end: 35, period: '생후 14~35일' },
    { type: '접종', title: 'BCG (결핵)', start: 0, end: 30, period: '생후 4주 이내' },
    { type: '접종', title: 'B형 간염 (1차)', start: 0, end: 1, period: '출생 시' },
    { type: '접종', title: 'B형 간염 (2차)', start: 30, end: 30, period: '생후 1개월' },
    { type: '접종', title: 'DTaP (1차)', start: 60, end: 60, period: '생후 2개월' },
    { type: '접종', title: '폴리오 (1차)', start: 60, end: 60, period: '생후 2개월' },
    { type: '접종', title: 'b형 헤모필루스 인플루엔자 (1차)', start: 60, end: 60, period: '생후 2개월' },
    { type: '접종', title: '폐렴구균 (1차)', start: 60, end: 60, period: '생후 2개월' },
    { type: '검진', title: '영유아 건강검진 (2차)', start: 120, end: 180, period: '생후 4~6개월' },
    { type: '접종', title: 'DTaP (2차)', start: 120, end: 120, period: '생후 4개월' },
    { type: '접종', title: '폴리오 (2차)', start: 120, end: 120, period: '생후 4개월' },
    { type: '접종', title: 'b형 헤모필루스 인플루엔자 (2차)', start: 120, end: 120, period: '생후 4개월' },
    { type: '접종', title: '폐렴구균 (2차)', start: 120, end: 120, period: '생후 4개월' },
    { type: '검진', title: '영유아 건강검진 (3차)', start: 180, end: 270, period: '생후 6~9개월' },
    { type: '접종', title: 'B형 간염 (3차)', start: 180, end: 180, period: '생후 6개월' },
    { type: '접종', title: 'DTaP (3차)', start: 180, end: 180, period: '생후 6개월' },
    { type: '접종', title: '폴리오 (3차)', start: 180, end: 180, period: '생후 6개월' },
    { type: '접종', title: 'b형 헤모필루스 인플루엔자 (3차)', start: 180, end: 180, period: '생후 6개월' },
    { type: '접종', title: '폐렴구균 (3차)', start: 180, end: 180, period: '생후 6개월' },
    { type: '검진', title: '영유아 건강검진 (4차)', start: 300, end: 360, period: '생후 10~12개월' },
    { type: '검진', title: '영유아 건강검진 (5차)', start: 360, end: 540, period: '생후 12~18개월' },
    { type: '접종', title: 'MMR (1차)', start: 360, end: 450, period: '생후 12~15개월' },
    { type: '접종', title: '수두 (1차)', start: 360, end: 450, period: '생후 12~15개월' },
    { type: '접종', title: '일본뇌염 (사백신 1차)', start: 360, end: 450, period: '생후 12~15개월' },
    { type: '검진', title: '영유아 건강검진 (6차)', start: 540, end: 720, period: '생후 18~24개월' },
    { type: '검진', title: '영유아 건강검진 (7차)', start: 1095, end: 1460, period: '생후 36~48개월' },
    { type: '검진', title: '영유아 건강검진 (8차)', start: 1460, end: 1825, period: '생후 48~60개월' }
];

function renderHealthSchedule(birthDateStr) {
    console.log("건강 스케줄 렌더링 시작. 생일:", birthDateStr);
    if (!birthDateStr) {
        console.warn("생일 데이터가 없어 스케줄을 계산할 수 없습니다.");
        return;
    }

    const birthDate = new Date(birthDateStr);
    birthDate.setHours(0, 0, 0, 0);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const diffTime = today - birthDate;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    const todayTasksContainer = document.getElementById('today-health-tasks');
    const fullScheduleList = document.getElementById('full-schedule-list');

    if (!todayTasksContainer || !fullScheduleList) {
        console.error("건강 스케줄 컨테이너를 찾을 수 없습니다! HTML 구조를 확인하세요.");
        return;
    }
    console.log("컨테이너 확인 완료. 루프 시작...");

    fullScheduleList.innerHTML = '';
    let todayTasksHtml = '';

    HEALTH_SCHEDULE.forEach(item => {
        let status = 'future';
        let statusText = '기한 전';
        let statusClass = 'future';

        if (diffDays >= item.start && diffDays <= item.end) {
            status = 'today';
            statusText = '진행 중';
            statusClass = 'today';
        } else if (diffDays > item.end) {
            status = 'completed';
            statusText = '완료 기한 지남';
            statusClass = 'done';
        }

        // 날짜 범위 계산
        const startDate = new Date(birthDate);
        startDate.setDate(birthDate.getDate() + item.start);
        const endDate = new Date(birthDate);
        endDate.setDate(birthDate.getDate() + item.end);

        const dateRangeStr = `${startDate.getFullYear()}.${String(startDate.getMonth() + 1).padStart(2, '0')}.${String(startDate.getDate()).padStart(2, '0')} ~ ${endDate.getFullYear()}.${String(endDate.getMonth() + 1).padStart(2, '0')}.${String(endDate.getDate()).padStart(2, '0')}`;

        const itemHtml = `
            <div class="schedule-item ${status}">
                <div class="info">
                    <span class="title">[${item.type}] ${item.title}</span>
                    <span class="period">${item.period} <small style="color: #00b894; margin-left:10px;">(${dateRangeStr})</small></span>
                </div>
                <span class="status-badge ${statusClass}">${statusText}</span>
            </div>
        `;

        fullScheduleList.innerHTML += itemHtml;

        // 현재 진행 중이거나 곧 다가올 일정 (또는 최근에 지난 일정 중 중요도가 높은 것)
        if (status === 'today') {
            todayTasksHtml += itemHtml;
        }
    });

    if (todayTasksHtml) {
        todayTasksContainer.innerHTML = todayTasksHtml;
    } else {
        // 진행 중인 일정이 없으면 가장 가까운 미래 일정 하나 보여주기
        const nextTask = HEALTH_SCHEDULE.find(item => item.start > diffDays);
        if (nextTask) {
            todayTasksContainer.innerHTML = `
                <p style="margin-bottom: 10px; font-size: 0.9rem; color: #888;">💡 현재 진행 중인 일정이 없습니다. 다음 일정을 준비하세요:</p>
                <div class="schedule-item future">
                    <div class="info">
                        <span class="title">[${nextTask.type}] ${nextTask.title}</span>
                        <span class="period">${nextTask.period} (D-${nextTask.start - diffDays})</span>
                    </div>
                    <span class="status-badge future">D-${nextTask.start - diffDays}</span>
                </div>
            `;
        } else {
            todayTasksContainer.innerHTML = '<p class="empty-msg">모든 주요 검진 및 접종 일정이 완료되었습니다! 🎉</p>';
        }
    }
}

