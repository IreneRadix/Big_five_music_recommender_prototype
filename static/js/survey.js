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
        
        // Генерация 44 вопросов
        this.questions = this.generateQuestions(4);
        
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
        
        // Определение групп вопросов для суммирования (индексы с 0)
        this.questionGroups = {
            group1: [0, 5, 10, 15, 20, 25, 30, 35, 40],     // 1,6,11,16,21,26,31,36,41
            group2: [1, 6, 11, 16, 21, 26, 31, 36, 41],     // 2,7,12,17,22,27,32,37,42
            group3: [2, 7, 12, 17, 22, 27, 32, 37, 42],     // 3,8,13,18,23,28,33,38,43
            group4: [3, 8, 13, 18, 23, 28, 33, 38],         // 4,9,14,19,24,29,34,39
            group5: [4, 9, 14, 19, 24, 29, 34, 39, 43]      // 5,10,15,20,25,30,35,40,44
        };
        
        // Переменные для хранения сумм по группам
        this.groupSums = {
            group1: 0,
            group2: 0,
            group3: 0,
            group4: 0,
            group5: 0
        };
        
        this.init();
    }
    
    generateQuestions(count) {
        const questions = [];
        const topics = [
            'качество обслуживания',
            'удобство сайта',
            'скорость работы',
            'ценовую политику',
            'ассортимент товаров',
            'доставку',
            'поддержку клиентов',
            'мобильное приложение',
            'бонусную программу',
            'акции и скидки',
            'информативность',
            'дизайн',
            'навигацию',
            'отзывы других покупателей',
            'процесс оформления заказа',
            'способы оплаты',
            'упаковку товаров',
            'качество товаров',
            'работу склада',
            'информирование о статусе заказа',
            'работу колл-центра',
            'возврат товаров',
            'обмен товаров',
            'гарантийное обслуживание',
            'сервисные центры',
            'доставку в регионы',
            'международную доставку',
            'работу курьеров',
            'пункты самовывоза',
            'работу с претензиями',
            'обратную связь',
            'персонализацию',
            'рекомендации товаров',
            'поиск на сайте',
            'фильтры товаров',
            'сравнение товаров',
            'отзывы о товарах',
            'фотографии товаров',
            'описания товаров',
            'характеристики товаров',
            'наличие на складе',
            'сроки доставки',
            'стоимость доставки',
            'общее впечатление'
        ];
        
        for (let i = 0; i < count; i++) {
            questions.push(`Как вы оцениваете ${topics[i % topics.length]}?`);
        }
        
        return questions;
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
            
            // Определяем группу вопроса для визуальной подсказки (опционально)
            const groupInfo = this.getQuestionGroup(globalIndex);
            
            return `
                <div class="question-item" data-question-index="${globalIndex}">
                    <div class="question-text">
                        ${globalIndex + 1}. ${question}
                        ${groupInfo ? `<span class="question-group">(Группа ${groupInfo})</span>` : ''}
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
    
    getQuestionGroup(index) {
        for (let [groupName, indices] of Object.entries(this.questionGroups)) {
            if (indices.includes(index)) {
                return groupName.replace('group', '');
            }
        }
        return null;
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
        
        // Для отладки - выводим суммы в консоль (можно удалить в продакшене)
        console.log('Текущие суммы по группам:', this.groupSums);
    }
    
    calculateGroupSums() {
        // Сброс сумм
        this.groupSums = {
            group1: 0,
            group2: 0,
            group3: 0,
            group4: 0,
            group5: 0
        };
        
        // Подсчет сумм по каждой группе
        for (let [groupName, indices] of Object.entries(this.questionGroups)) {
            let sum = 0;
            let answeredCount = 0;
            
            for (let index of indices) {
                if (this.userData.answers[index]) {
                    sum += this.userData.answers[index];
                    answeredCount++;
                }
            }
            
            // Сохраняем сумму только если все вопросы в группе отвечены
            if (answeredCount === indices.length) {
                this.groupSums[groupName] = sum;
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
        
        // Визуально отмечаем завершенность страницы
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
        
        if (allAnswered) {
            // Финальный подсчет сумм
            this.calculateGroupSums();
            
            if (this.currentPage === this.totalPages) {
                this.submitBtn.classList.remove('hidden');
            }
        }
    }
    
    goToPreviousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderCurrentPage();
        }
    }
    
    goToNextPage() {
        // Проверяем, все ли вопросы на текущей странице отвечены
        const startIndex = (this.currentPage - 1) * this.questionsPerPage;
        const endIndex = Math.min(startIndex + this.questionsPerPage, this.questions.length);
        
        let allCurrentPageAnswered = true;
        for (let i = startIndex; i < endIndex; i++) {
            if (!this.userData.answers[i]) {
                allCurrentPageAnswered = false;
                document.getElementById(`questionError-${i}`).textContent = 
                    'Пожалуйста, ответьте на этот вопрос';
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
        
        // Проверка пола
        if (!this.userData.gender) {
            document.getElementById('genderError').textContent = 'Выберите пол';
            isValid = false;
        }
        
        // Проверка возраста
        if (!this.validateAge()) {
            isValid = false;
        }
        
        // Проверка всех ответов
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
        
        // Финальный подсчет сумм перед отправкой
        this.calculateGroupSums();
        
        // Блокируем кнопку отправки
        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Отправка...';
        
        try {
            // Подготавливаем данные для отправки
            const dataToSend = {
                personal: {
                    gender: this.userData.gender,
                    age: this.userData.age
                },
                answers: this.userData.answers,
                groupSums: this.groupSums,
                summary: {
                    totalQuestions: this.questions.length,
                    answeredQuestions: Object.keys(this.userData.answers).length,
                    timestamp: new Date().toISOString()
                }
            };
            
            console.log('Отправляемые данные с суммами по группам:', dataToSend);
            
            // Отправка данных на сервер
            const response = await this.sendToServer(dataToSend);
            
            if (response.ok) {
                // Показываем пользователю результаты по группам
                //this.showGroupResults();
                //this.resetForm();
                window.location.href = '/feed/' + localStorage.getItem('user_name') ;
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
    
    showGroupResults() {
        // Создаем красивое отображение результатов по группам
        const resultsHTML = `
            <div class="group-results">
                <h3>Результаты по категориям:</h3>
                <div class="result-item">
                    <span>Группа 1 (вопросы 1,6,11,16,21,26,31,36,41):</span>
                    <strong>${this.groupSums.group1} баллов</strong>
                </div>
                <div class="result-item">
                    <span>Группа 2 (вопросы 2,7,12,17,22,27,32,37,42):</span>
                    <strong>${this.groupSums.group2} баллов</strong>
                </div>
                <div class="result-item">
                    <span>Группа 3 (вопросы 3,8,13,18,23,28,33,38,43):</span>
                    <strong>${this.groupSums.group3} баллов</strong>
                </div>
                <div class="result-item">
                    <span>Группа 4 (вопросы 4,9,14,19,24,29,34,39):</span>
                    <strong>${this.groupSums.group4} баллов</strong>
                </div>
                <div class="result-item">
                    <span>Группа 5 (вопросы 5,10,15,20,25,30,35,40,44):</span>
                    <strong>${this.groupSums.group5} баллов</strong>
                </div>
            </div>
        `;
        
        this.resultDiv.innerHTML = resultsHTML;
        this.resultDiv.className = 'success';
    }
    
    async sendToServer(data) {
        // Имитация отправки на сервер
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
        // Сбрасываем выделение пола
        this.genderBtns.forEach(btn => btn.classList.remove('active'));
        
        // Сбрасываем возраст
        this.ageInput.value = '';
        
        // Очищаем ответы
        this.userData = {
            gender: null,
            age: null,
            answers: {}
        };
        
        // Сбрасываем суммы групп
        this.groupSums = {
            group1: 0,
            group2: 0,
            group3: 0,
            group4: 0,
            group5: 0
        };
        
        // Возвращаемся на первую страницу
        this.currentPage = 1;
        this.renderCurrentPage();
        this.updateProgress();
        
        // Очищаем ошибки
        document.querySelectorAll('.error').forEach(error => {
            error.textContent = '';
        });
    }
}

// Добавляем стили для отображения результатов групп в CSS (можно добавить в style.css)
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
`;

// Добавляем стили в документ
const styleSheet = document.createElement("style");
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    new PaginatedSurveyComponent();
});