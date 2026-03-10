class SurveyComponent {
    constructor() {
        this.form = document.getElementById('surveyForm');
        this.genderBtns = document.querySelectorAll('.gender-btn');
        this.ageInput = document.getElementById('age');
        this.questionsContainer = document.getElementById('questions');
        this.submitBtn = document.getElementById('submitBtn');
        this.resultDiv = document.getElementById('result');
        
        this.questions = [
            'Как вы оцениваете качество обслуживания?',
            'Насколько вы удовлетворены работой сайта?',
            'Как бы вы оценили скорость ответа поддержки?',
            'Насколько вероятно, что вы порекомендуете нас друзьям?',
            'Как вы оцениваете соотношение цены и качества?'
        ];
        
        this.userData = {
            gender: null,
            age: null,
            answers: {}
        };
        
        this.init();
    }
    
    init() {
        this.renderQuestions();
        this.setupEventListeners();
    }
    
    renderQuestions() {
        this.questionsContainer.innerHTML = this.questions.map((question, index) => `
            <div class="question-item" data-question-index="${index}">
                <div class="question-text">${index + 1}. ${question}</div>
                <div class="rating" id="rating-${index}">
                    ${[1,2,3,4,5].map(num => `
                        <button type="button" class="rating-btn" data-value="${num}">${num}</button>
                    `).join('')}
                </div>
                <div class="error" id="questionError-${index}"></div>
            </div>
        `).join('');
    }
    
    setupEventListeners() {
        // Выбор пола
        this.genderBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleGenderSelect(e));
        });
        
        // Валидация возраста
        this.ageInput.addEventListener('input', () => this.validateAge());
        this.ageInput.addEventListener('blur', () => this.validateAge());
        
        // Обработка оценок
        document.querySelectorAll('.rating').forEach(rating => {
            rating.addEventListener('click', (e) => this.handleRatingClick(e));
        });
        
        // Отправка формы
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }
    
    handleGenderSelect(e) {
        const selectedBtn = e.target;
        const gender = selectedBtn.dataset.gender;
        
        // Убираем активный класс у всех кнопок
        this.genderBtns.forEach(btn => btn.classList.remove('active'));
        
        // Добавляем активный класс выбранной кнопке
        selectedBtn.classList.add('active');
        
        // Сохраняем данные
        this.userData.gender = gender;
        
        // Убираем ошибку
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
        const questionIndex = questionItem.dataset.questionIndex;
        const value = btn.dataset.value;
        
        // Убираем выделение у всех кнопок в этом вопросе
        rating.querySelectorAll('.rating-btn').forEach(b => {
            b.classList.remove('selected');
        });
        
        // Выделяем выбранную кнопку
        btn.classList.add('selected');
        
        // Сохраняем ответ
        this.userData.answers[questionIndex] = parseInt(value);
        
        // Убираем ошибку
        document.getElementById(`questionError-${questionIndex}`).textContent = '';
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
        
        // Проверка ответов на вопросы
        this.questions.forEach((_, index) => {
            if (!this.userData.answers[index]) {
                document.getElementById(`questionError-${index}`).textContent = 
                    'Пожалуйста, оцените этот вопрос';
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateForm()) {
            this.showResult('Пожалуйста, заполните все поля', 'error');
            return;
        }
        
        // Блокируем кнопку отправки
        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Отправка...';
        
        try {
            // Отправка данных на сервер
            const response = await this.sendToServer(this.userData);
            
            if (response.ok) {
                this.showResult('Данные успешно отправлены!', 'success');
                this.resetForm();
            } else {
                throw new Error('Ошибка сервера');
            }
        } catch (error) {
            this.showResult('Ошибка при отправке данных. Попробуйте позже.', 'error');
            console.error('Ошибка:', error);
        } finally {
            // Разблокируем кнопку
            this.submitBtn.disabled = false;
            this.submitBtn.textContent = 'Отправить';
        }
    }
    
    async sendToServer(data) {
        // Имитация отправки на сервер
        // Замените URL на ваш реальный эндпоинт
        return fetch('https://your-server.com/api/survey', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        // Для тестирования без сервера раскомментируйте:
        /*
        return new Promise((resolve) => {
            setTimeout(() => {
                console.log('Отправленные данные:', data);
                resolve({ ok: true });
            }, 1500);
        });
        */
    }
    
    showResult(message, type) {
        this.resultDiv.textContent = message;
        this.resultDiv.className = type;
        
        // Автоматически скрываем сообщение через 5 секунд
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
        
        // Сбрасываем оценки
        document.querySelectorAll('.rating-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        
        // Очищаем данные
        this.userData = {
            gender: null,
            age: null,
            answers: {}
        };
        
        // Очищаем ошибки
        document.querySelectorAll('.error').forEach(error => {
            error.textContent = '';
        });
    }
}

// Инициализация компонента после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    new SurveyComponent();
});