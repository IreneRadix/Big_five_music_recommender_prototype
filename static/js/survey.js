const API_BASE = 'http://localhost:5000/api';

class PaginatedSurveyComponent {
    constructor() {
        this.form = document.getElementById('surveyForm');
        this.genderBtns = document.querySelectorAll('.gender-btn');
        this.ageInput = document.getElementById('age');
        this.questionsContainer = document.getElementById('questionsContainer');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.submitBtn = document.getElementById('submitBtn');
        this.pageIndicator = document.getElementById('pageIndicator');
        this.progressBar = document.getElementById('progressBar');
        this.progressText = document.getElementById('progressText');
        this.resultDiv = document.getElementById('result');
        
        // Вопросы для группы 1 (экстраверсия/открытость опыту)
        this.group1Questions = [
            "Я разговорчив(а)",
            "Мне свойственна оригинальность и творчество, у меня много новых идей",
            "Я замкнутый(ая)",
            "Я интересуюсь массой разных вещей",
            "У меня много энергии",
            "Мне свойственны глубокие мысли и/или остроумие",
            "Я излучаю энтузиазм и заряжаю им окружающих",
            "У меня богатое воображение",
            "Я обычно молчалив(а)"
        ];
        
        // Вопросы для группы 5 (открытость опыту/интеллект)
        this.group5Questions = [
            "Я изобретателен(на)",
            "Я уверена(а) в себе",
            "Я высоко ценю искусство и эстетические переживания",
            "Порой я застенчив(а)",
            "Я предпочитаю рутинную работу",
            "Я общителен(на)",
            "Я люблю развивать идеи и размышлять",
            "У меня мало увлечений, связанных с искусством",
            "Я разбираюсь в искусстве, музыке и/или литературе"
        ];
        
        // Объединяем вопросы групп 1 и 5
        this.questions = [...this.group1Questions, ...this.group5Questions];
        
        // Настройки пагинации
        this.questionsPerPage = 4;
        this.currentPage = 1;
        this.totalPages = Math.ceil(this.questions.length / this.questionsPerPage);
        
        // Данные пользователя
        this.userData = {
            gender: null,
            age: null,
            answers: {}
        };
        
        // Переменные для хранения сумм по группам
        this.groupSums = {
            group1: 0,
            group5: 0
        };
        
        this.init();
    }
    
    init() {
        this.renderCurrentPage();
        this.setupEventListeners();
        this.updateProgress();
        this.checkAllQuestionsAnswered();
    }
    
    renderCurrentPage() {
        const startIndex = (this.currentPage - 1) * this.questionsPerPage;
        const endIndex = Math.min(startIndex + this.questionsPerPage, this.questions.length);
        const currentQuestions = this.questions.slice(startIndex, endIndex);
        
        this.questionsContainer.innerHTML = currentQuestions.map((question, localIndex) => {
            const globalIndex = startIndex + localIndex;
            const savedAnswer = this.userData.answers[globalIndex];
            
            // Определяем группу вопроса
            let groupNumber = globalIndex < this.group1Questions.length ? 1 : 5;
            
            return `
                <div class="question-item" data-question-index="${globalIndex}">
                    <div class="question-text">
                        ${globalIndex + 1}. ${question}
                        <span class="question-group">(Группа ${groupNumber})</span>
                    </div>
                    <div class="rating" id="rating-${globalIndex}">
                        ${[1,2,3,4,5].map(num => `
                            <button type="button" 
                                    class="rating-btn ${savedAnswer === num ? 'selected' : ''}" 
                                    data-value="${num}">${num}</button>
                        `).join('')}
                    </div>
                    <div class="error" id="questionError-${globalIndex}"></div>
                </div>
            `;
        }).join('');
        
        // Обновляем индикатор страницы
        this.pageIndicator.textContent = `Страница ${this.currentPage}/${this.totalPages}`;
        
        // Обновляем состояние кнопок навигации
        this.prevBtn.disabled = this.currentPage === 1;
        this.nextBtn.disabled = this.currentPage === this.totalPages;
        
        // Показываем/скрываем кнопку отправки
        this.submitBtn.classList.toggle('hidden', this.currentPage !== this.totalPages);
    }
    
    setupEventListeners() {
        // Выбор пола
        this.genderBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleGenderSelect(e));
        });
        
        // Валидация возраста
        this.ageInput.addEventListener('input', () => this.validateAge());
        this.ageInput.addEventListener('blur', () => this.validateAge());
        
        // Обработка оценок (делегирование событий)
        this.questionsContainer.addEventListener('click', (e) => this.handleRatingClick(e));
        
        // Навигация
        this.prevBtn.addEventListener('click', () => this.goToPreviousPage());
        this.nextBtn.addEventListener('click', () => this.goToNextPage());
        
        // Отправка формы
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }
    
    handleGenderSelect(e) {
        const selectedBtn = e.target;
        const gender = selectedBtn.dataset.gender;
        
        this.genderBtns.forEach(btn => btn.classList.remove('active'));
        selectedBtn.classList.add('active');
        
        this.userData.gender = gender;
        document.getElementById('genderError').textContent = '';
    }
    
    validateAge() {
        const age = parseInt(this.ageInput.value);
        const errorElement = document.getElementById('ageError');
        
        if (!this.ageInput.value) {
            errorElement.textContent = 'Пожалуйста, введите возраст';
            this.userData.age = null;
            return false;
        }
        
        if (isNaN(age) || age < 1 || age > 120) {
            errorElement.textContent = 'Введите корректный возраст (от 1 до 120 лет)';
            this.userData.age = null;
            return false;
        }
        
        errorElement.textContent = '';
        this.userData.age = age;
        return true;
    }
    
    handleRatingClick(e) {
        const btn = e.target.closest('.rating-btn');
        if (!btn) return;
        
        const rating = btn.closest('.rating');
        const questionItem = rating.closest('.question-item');
        const questionIndex = parseInt(questionItem.dataset.questionIndex);
        const value = parseInt(btn.dataset.value);
        
        // Убираем выделение у всех кнопок в этом вопросе
        rating.querySelectorAll('.rating-btn').forEach(b => {
            b.classList.remove('selected');
        });
        
        // Выделяем выбранную кнопку
        btn.classList.add('selected');
        
        // Сохраняем ответ
        this.userData.answers[questionIndex] = value;
        
        // Пересчитываем суммы по группам
        this.calculateGroupSums();
        
        // Убираем ошибку
        document.getElementById(`questionError-${questionIndex}`).textContent = '';
        
        // Обновляем прогресс
        this.updateProgress();
        
        // Проверяем, все ли вопросы отвечены на текущей странице
        this.checkCurrentPageCompletion();
        
        console.log('Текущие суммы по группам:', this.groupSums);
    }
    
    calculateGroupSums() {
        // Сброс сумм
        this.groupSums = {
            group1: 0,
            group5: 0
        };
        
        // Проходим по всем сохранённым ответам
        for (const [idx, answerValue] of Object.entries(this.userData.answers)) {
            const index = parseInt(idx);
            if (index < this.group1Questions.length) {
                this.groupSums.group1 += answerValue;
            } else {
                this.groupSums.group5 += answerValue;
            }
        }
    }
    
    checkCurrentPageCompletion() {
        const startIndex = (this.currentPage - 1) * this.questionsPerPage;
        const endIndex = Math.min(startIndex + this.questionsPerPage, this.questions.length);
        
        let allAnswered = true;
        for (let i = startIndex; i < endIndex; i++) {
            if (!this.userData.answers[i]) {
                allAnswered = false;
                break;
            }
        }
        
        if (allAnswered) {
            this.pageIndicator.style.color = '#28a745';
        } else {
            this.pageIndicator.style.color = '#666';
        }
    }
    
    updateProgress() {
        const answeredCount = Object.keys(this.userData.answers).length;
        const totalQuestions = this.questions.length;
        const percentage = (answeredCount / totalQuestions) * 100;
        
        this.progressBar.style.width = `${percentage}%`;
        this.progressText.textContent = `${answeredCount}/${totalQuestions} вопросов отвечено`;
    }
    
    checkAllQuestionsAnswered() {
        const allAnswered = Object.keys(this.userData.answers).length === this.questions.length;
        
        if (allAnswered && this.currentPage === this.totalPages) {
            this.submitBtn.classList.remove('hidden');
        }
    }
    
    goToPreviousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderCurrentPage();
        }
    }
    
    goToNextPage() {
        const startIndex = (this.currentPage - 1) * this.questionsPerPage;
        const endIndex = Math.min(startIndex + this.questionsPerPage, this.questions.length);
        
        let allCurrentPageAnswered = true;
        for (let i = startIndex; i < endIndex; i++) {
            if (!this.userData.answers[i]) {
                allCurrentPageAnswered = false;
                const errorElement = document.getElementById(`questionError-${i}`);
                if (errorElement) {
                    errorElement.textContent = 'Пожалуйста, ответьте на этот вопрос';
                }
            }
        }
        
        if (!allCurrentPageAnswered) {
            this.showResult('Ответьте на все вопросы на этой странице', 'error');
            return;
        }
        
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.renderCurrentPage();
            this.checkAllQuestionsAnswered();
        }
    }
    
    validateForm() {
        let isValid = true;
        
        if (!this.userData.gender) {
            document.getElementById('genderError').textContent = 'Выберите пол';
            isValid = false;
        }
        
        if (!this.validateAge()) {
            isValid = false;
        }
        
        if (Object.keys(this.userData.answers).length !== this.questions.length) {
            this.showResult('Ответьте на все вопросы перед отправкой', 'error');
            isValid = false;
        }
        
        return isValid;
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateForm()) {
            return;
        }
        
        this.calculateGroupSums();
        
        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Отправка...';
        
        try {
            const dataToSend = {
                personal: {
                    gender: this.userData.gender,
                    age: this.userData.age,
                    id: localStorage.getItem('user_id')
                },
                answers: this.userData.answers,
                groupSums: this.groupSums,
                summary: {
                    totalQuestions: this.questions.length,
                    answeredQuestions: Object.keys(this.userData.answers).length,
                    timestamp: new Date().toISOString()
                }
            };
            
            console.log('Отправляемые данные:', dataToSend);
            
            const response = await this.sendToServer(dataToSend);
            
            if (response.ok) {
                window.location.href = '/login';
            } else {
                throw new Error('Ошибка сервера');
            }
        } catch (error) {
            this.showResult('Ошибка при отправке данных. Попробуйте позже.', 'error');
            console.error('Ошибка:', error);
        } finally {
            this.submitBtn.disabled = false;
            this.submitBtn.textContent = 'Отправить ответы';
        }
    }
    
    async sendToServer(data) {
        return fetch(`${API_BASE}/survey`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }
    
    showResult(message, type) {
        this.resultDiv.textContent = message;
        this.resultDiv.className = type;
        
        setTimeout(() => {
            this.resultDiv.textContent = '';
            this.resultDiv.className = '';
        }, 5000);
    }
    
    resetForm() {
        this.genderBtns.forEach(btn => btn.classList.remove('active'));
        this.ageInput.value = '';
        
        this.userData = {
            gender: null,
            age: null,
            answers: {}
        };
        
        this.groupSums = {
            group1: 0,
            group5: 0
        };
        
        this.currentPage = 1;
        this.renderCurrentPage();
        this.updateProgress();
        
        document.querySelectorAll('.error').forEach(error => {
            error.textContent = '';
        });
    }
}

// Стили
const additionalStyles = `
.group-results {
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 8px;
    margin-top: 20px;
}

.group-results h3 {
    color: #333;
    margin-bottom: 15px;
    text-align: center;
}

.result-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    margin-bottom: 8px;
    background-color: white;
    border-radius: 5px;
    border-left: 4px solid #007bff;
}

.result-item strong {
    color: #28a745;
    font-size: 18px;
}

.question-group {
    font-size: 12px;
    color: #6c757d;
    margin-left: 10px;
    background-color: #e9ecef;
    padding: 2px 6px;
    border-radius: 3px;
}

.rating {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}

.rating-btn {
    width: 40px;
    height: 40px;
    border: 1px solid #ddd;
    background: white;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
}

.rating-btn.selected {
    background: #007bff;
    color: white;
    border-color: #007bff;
}

.question-item {
    margin-bottom: 25px;
    padding: 15px;
    border: 1px solid #eee;
    border-radius: 8px;
}
`;

const styleSheet = document.createElement("style");
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

document.addEventListener('DOMContentLoaded', () => {
    new PaginatedSurveyComponent();
});