// Vue приложение
const { createApp, ref, onMounted } = Vue

// Компонент главной страницы
const IndexPage = {
    template: `
        <div>
            <header>
                <img class="Logo" src="/static/img/Logo.svg" alt="">
                <menu>
                    <img class="notification" src="/static/img/notification.svg" alt="">
                    <img class="profile" src="/static/img/person men.png" alt="">
                </menu>
            </header>

            <main>
                <nav>
                    <button class="model" @click="goToModel">
                        <img class="imgModel" src="/static/img/model.svg" alt="">
                    </button>
                    <button class="linkStelaz">
                        Перейти к стеллажам
                        <img class="imgStelaz" src="/static/img/export.svg" alt="">
                    </button>
                    <button @click="openUploadModal" class="btnDownload">
                        Загрузить материал
                        <img class="imgDown" src="/static/img/download.svg" alt="">
                    </button>
                </nav>

                <!-- Модальное окно загрузки -->
                <div>
                    <div class="overlay" @click="closeUploadModal" v-show="uploadModalOpen"></div>
                    <div class="LoadingScreen" v-show="uploadModalOpen">
                        <div class="VerhLoadingScreen">
                            <h3>Загрузка файлов</h3>
                            <button class="close-x" @click="closeUploadModal">
                                <img src="/static/img/close-x.svg" alt="">
                            </button>
                        </div>
                        <div class="listFiles">
                            <span class="file" v-html="fileNames"></span>
                        </div>
                        <form @submit.prevent="uploadFiles">
                            <label class="file-btn" for="showUploadForm">Выбрать файлы</label>
                            <button class="downloadBtn2" type="submit">Загрузить</button>
                            <input id="showUploadForm" name="files" multiple class="custom-file-input" type="file" accept=".mp4, .mov, .avi, .jpg, .jpeg, .png" @change="updateFileLabel">
                        </form>
                    </div>
                </div>

                <!-- Галерея -->
                <div class="container_gallery">
                    <h2>Галерея фотографий ({{ photos.length }} фото)</h2>
                    <div v-if="photos.length" class="gallery">
                        <div v-for="photo in photos" :key="photo.id">
                            <img 
                                v-if="photo.processed_photo"
                                :src="'/static/' + photo.processed_photo"
                                class="thumbnail"
                                @click="openZoom(photo)"
                            >
                            <div v-else class="processing-placeholder">
                                <p>В обработке...</p>
                            </div>
                            <h3 class="name">{{ formatDate(photo.photo_date) }}</h3>
                            <span v-if="photo.processed_photo" class="badge">Обработано</span>
                        </div>
                    </div>
                    <p v-else>Нет обработанных фотографий. Загрузите фото или видео для анализа.</p>
                </div>

                <!-- Увеличенное фото -->
                <div class="zoomed" @click="closeZoom" v-show="zoomModalOpen">
                    <img :src="zoomImageSrc" alt="Zoomed Image">
                    <div class="shelfInfo">Номер полки: {{ currentPhoto?.id }}</div>
                    <button @click.stop="deleteImage">Удалить</button>
                </div>

                <!-- Активные сервисы -->
                <div class="services-section">
                    <div class="services-panel">
                        <div class="services-header">
                            <h3>Активные сервисы</h3>
                            <button class="refresh-btn" @click="loadServices">Обновить</button>
                        </div>
                        <div v-if="servicesLoading" class="loading-message">Загрузка...</div>
                        <div v-else-if="services.length === 0" class="empty-message">Нет активных сервисов</div>
                        <div v-else class="services-list">
                            <div v-for="service in services" :key="service.service_id" class="service-item">
                                <div class="service-info">
                                    <div class="service-name">
                                        <span class="service-status"></span>
                                        {{ service.service_name || service.service_id }}
                                    </div>
                                    <div class="service-address">
                                        {{ service.address }}:{{ service.port }}
                                    </div>
                                </div>
                                <div class="service-tags">
                                    <span v-for="tag in (service.tags || []).slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
                                    <span v-if="!service.tags || service.tags.length === 0" class="tag">нет тегов</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    `,
    setup(props, { emit }) {
        const photos = ref([])
        const uploadModalOpen = ref(false)
        const zoomModalOpen = ref(false)
        const currentPhoto = ref(null)
        const zoomImageSrc = ref('')
        const files = ref([])
        const fileNames = ref('Нет загружаемых файлов')
        const services = ref([])
        const servicesLoading = ref(true)

        const loadServices = async () => {
            servicesLoading.value = true
            try {
                const response = await fetch('/discovery/services')
                services.value = await response.json()
            } catch (error) {
                console.error('Ошибка загрузки сервисов:', error)
            } finally {
                servicesLoading.value = false
            }
        }

        const loadPhotos = async () => {
            try {
                const response = await fetch('/api/photos')
                photos.value = await response.json()
            } catch (error) {
                console.error('Ошибка загрузки фото:', error)
            }
        }

        const formatDate = (dateString) => {
            const date = new Date(dateString)
            return date.toLocaleDateString('ru-RU', { 
                day: 'numeric', 
                month: 'long', 
                year: 'numeric' 
            })
        }

        const goToModel = () => {
            emit('navigate', 'model')
        }

        const openUploadModal = () => {
            uploadModalOpen.value = true
        }

        const closeUploadModal = () => {
            uploadModalOpen.value = false
        }

        const updateFileLabel = (event) => {
            const selectedFiles = event.target.files
            if (selectedFiles.length > 0) {
                fileNames.value = Array.from(selectedFiles).map(f => f.name).join('<br>')
                files.value = selectedFiles
            } else {
                fileNames.value = 'Нет загружаемых файлов'
            }
        }

        const uploadFiles = async () => {
            if (files.value.length === 0) {
                alert('Пожалуйста, добавьте файлы для загрузки.')
                return
            }

            const formData = new FormData()
            for (let i = 0; i < files.value.length; i++) {
                formData.append('files', files.value[i])
            }

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                if (response.ok) {
                    closeUploadModal()
                    await loadPhotos()
                    alert('Файлы успешно загружены!')
                    // Очищаем поле файлов
                    files.value = []
                    fileNames.value = 'Нет загружаемых файлов'
                    const fileInput = document.getElementById('showUploadForm')
                    if (fileInput) fileInput.value = ''
                }
            } catch (error) {
                console.error('Ошибка загрузки:', error)
                alert('Ошибка при загрузке файлов')
            }
        }

        const openZoom = (photo) => {
            currentPhoto.value = photo
            zoomImageSrc.value = '/static/' + photo.processed_photo
            zoomModalOpen.value = true
        }

        const closeZoom = () => {
            zoomModalOpen.value = false
            currentPhoto.value = null
        }

        const deleteImage = async () => {
            if (!confirm('Удалить это фото?')) return
            
            try {
                const response = await fetch(`/api/photos/${currentPhoto.value.id}`, {
                    method: 'DELETE'
                })
                if (response.ok) {
                    closeZoom()
                    await loadPhotos()
                }
            } catch (error) {
                console.error('Ошибка удаления:', error)
            }
        }

        onMounted(() => {
            loadPhotos()
            loadServices()
            setInterval(loadServices, 30000)
        })

        return {
            photos,
            uploadModalOpen,
            zoomModalOpen,
            currentPhoto,
            zoomImageSrc,
            fileNames,
            services,
            servicesLoading,
            formatDate,
            goToModel,
            openUploadModal,
            closeUploadModal,
            updateFileLabel,
            uploadFiles,
            openZoom,
            closeZoom,
            deleteImage,
            loadServices
        }
    }
}

// Компонент страницы модели
const ModelPage = {
    template: `
        <div class="model-page">
            <div class="left">
                <!-- Обучение модели -->
                <div class="blockOne">
                    <h2>Обучение модели</h2>
                    <form @submit.prevent="trainModel">
                        <label for="datasets">Варианты датасетов</label>
                        <select id="datasets" v-model="selectedDataset" required>
                            <option v-for="ds in datasets" :key="ds.id" :value="ds.dataset">
                                {{ ds.dataset.split('\\\\').pop() }}
                            </option>
                        </select><br>

                        <p>Параметры</p>
                        <div class="form-group">
                            <input class="parOne" type="text" v-model="modelName" placeholder="Название модели" required>
                        </div>
                        <div class="form-group">
                            <input class="parOne" type="number" v-model="imgsz" placeholder="Размер изображения" required>
                        </div>
                        <div class="form-group">
                            <input class="parOne" type="number" v-model="epochs" placeholder="Количество эпох" required>
                        </div>
                        <div class="form-group">
                            <input class="parOne" type="number" v-model="batch" placeholder="Размер батча" required>
                        </div>
                        <div class="form-group">
                            <input class="parOne" type="number" v-model="savePeriod" placeholder="Период сохранения" required>
                        </div>

                        <button class="btnStartTrain" type="submit">Запустить обучение</button>
                    </form>
                </div>

                <div class="BlockAddClass">
                    <h2>Создание класса</h2>
                    <form @submit.prevent="createClass">
                        <select v-model="selectedClassDataset" required>
                            <option v-for="ds in datasets" :key="ds.id" :value="ds.dataset">
                                {{ ds.dataset.split('\\\\').pop() }}
                            </option>
                        </select>
                        <input class="parTwoClass" type="text" v-model="className" placeholder="Название класса" required>
                        <button class="btnAddClass" type="submit">Создать класс</button>
                    </form>
                </div>
            </div>

            <div class="right">
                <button class="btnBack" @click="goToGallery">Вернуться в галерею</button>

                <div class="blockTwo">
                    <h2>Создание нового датасета</h2>

                    <div class="listFiles">
                        <label class="fileList">Список файлов</label>
                        <div class="inputsval1">
                            <label class="inputsval">
                                <input type="checkbox" v-model="showAnnotatedOnly" @change="filterFiles">
                                Только с разметкой
                            </label>
                        </div>

                        <select size="20" v-model="selectedPhoto" @change="updateImage">
                            <option v-for="photo in filteredPhotos" :key="photo.id" :value="photo.photo" :data-txt="photo.txt">
                                {{ getFilename(photo.photo) }}
                            </option>
                        </select>
                    </div>

                    <form @submit.prevent="createDataset">
                        <div class="addPhoto">
                            <input class="parTwoPhoto" type="number" v-model="numPhotos" placeholder="Количество фотографий" min="1" :max="nonEmptyCount" required>
                            <button @click="openUploadModal" type="button" class="btnDownload">Загрузить фотографии</button>
                        </div>

                        <input class="parTwo" type="text" v-model="datasetName" required placeholder="Название датасета">
                        <input class="parTwo" type="number" v-model="trainSize" min="0" max="1" step="0.01" required placeholder="Размер train выборки">
                        <input class="parTwo" type="number" v-model="valSize" min="0" max="1" step="0.01" required placeholder="Размер val выборки">

                        <button class="btnAddDataSet" type="submit">Сохранить датасет</button>
                    </form>
                </div>
            </div>

            <!-- Модальное окно загрузки -->
            <div>
                <div class="overlay" @click="closeUploadModal" v-show="uploadModalOpen"></div>
                <div class="LoadingScreen" v-show="uploadModalOpen">
                    <div class="VerhLoadingScreen">
                        <h3>Загрузка файлов</h3>
                        <button class="close-x" @click="closeUploadModal">
                            <img src="/static/img/close-x.svg" alt="">
                        </button>
                    </div>
                    <div class="listFiles">
                        <span class="file" v-html="fileNames"></span>
                    </div>
                    <form @submit.prevent="uploadModelFiles">
                        <label class="file-btn" for="modelUploadInput">Выбрать файлы</label>
                        <button class="downloadBtn2" type="submit">Загрузить</button>
                        <input id="modelUploadInput" ref="fileInput" multiple class="custom-file-input" type="file" accept=".jpg, .jpeg, .png, .txt" @change="updateModelFileLabel">
                    </form>
                </div>
            </div>
        </div>
    `,
    setup(props, { emit }) {
        const datasets = ref([])
        const photos = ref([])
        const selectedDataset = ref('')
        const modelName = ref('')
        const imgsz = ref(640)
        const epochs = ref(100)
        const batch = ref(16)
        const savePeriod = ref(10)
        const selectedClassDataset = ref('')
        const className = ref('')
        const showAnnotatedOnly = ref(false)
        const selectedPhoto = ref('')
        const filteredPhotos = ref([])
        const numPhotos = ref(0)
        const datasetName = ref('')
        const trainSize = ref(0.8)
        const valSize = ref(0.2)
        const nonEmptyCount = ref(0)
        
        // Модальное окно
        const uploadModalOpen = ref(false)
        const modelFiles = ref([])
        const fileNames = ref('Нет загружаемых файлов')
        const fileInput = ref(null)

        const loadData = async () => {
            try {
                const datasetsRes = await fetch('/api/datasets')
                datasets.value = await datasetsRes.json()
                
                const photosRes = await fetch('/api/photos?modul=1')
                const allPhotos = await photosRes.json()
                photos.value = allPhotos
                filterFiles()
                
                nonEmptyCount.value = photos.value.filter(p => p.txt).length
                numPhotos.value = nonEmptyCount.value
            } catch (error) {
                console.error('Ошибка загрузки:', error)
            }
        }

        const getFilename = (path) => {
            return path.split('/').pop()
        }

        const filterFiles = () => {
            if (showAnnotatedOnly.value) {
                filteredPhotos.value = photos.value.filter(p => p.txt)
            } else {
                filteredPhotos.value = photos.value
            }
        }

        const updateImage = () => {
            // Обновляем выбранное изображение
            emit('image-selected', selectedPhoto.value)
        }

        const trainModel = async () => {
            const formData = new FormData()
            formData.append('selected_dataset', selectedDataset.value)
            formData.append('model_name', modelName.value)
            formData.append('imgsz', imgsz.value)
            formData.append('epochs', epochs.value)
            formData.append('batch', batch.value)
            formData.append('save_period', savePeriod.value)
            
            try {
                const response = await fetch('/train', {
                    method: 'POST',
                    body: formData
                })
                if (response.ok) {
                    alert('Обучение запущено!')
                }
            } catch (error) {
                console.error('Ошибка:', error)
            }
        }

        const createClass = async () => {
            const formData = new FormData()
            formData.append('selected_dataset', selectedClassDataset.value)
            formData.append('class_name', className.value)
            
            try {
                const response = await fetch('/create_class', {
                    method: 'POST',
                    body: formData
                })
                if (response.ok) {
                    alert('Класс создан!')
                    className.value = ''
                }
            } catch (error) {
                console.error('Ошибка:', error)
            }
        }

        const createDataset = async () => {
            const formData = new FormData()
            formData.append('num_photos', numPhotos.value)
            formData.append('dataset_name', datasetName.value)
            formData.append('train_size', trainSize.value)
            formData.append('val_size', valSize.value)
            
            try {
                const response = await fetch('/copy_photos', {
                    method: 'POST',
                    body: formData
                })
                const result = await response.json()
                if (response.ok) {
                    alert('Датасет создан!')
                    await loadData()
                } else if (result.exists) {
                    if (confirm('Папка уже существует. Продолжить?')) {
                        const confirmResponse = await fetch('/copy_photos', {
                            method: 'POST',
                            body: formData
                        })
                        if (confirmResponse.ok) {
                            alert('Датасет обновлен!')
                        }
                    }
                }
            } catch (error) {
                console.error('Ошибка:', error)
            }
        }

        const openUploadModal = () => {
            uploadModalOpen.value = true
        }

        const closeUploadModal = () => {
            uploadModalOpen.value = false
        }

        const updateModelFileLabel = (event) => {
            const selectedFiles = event.target.files
            if (selectedFiles.length > 0) {
                fileNames.value = Array.from(selectedFiles).map(f => f.name).join('<br>')
                modelFiles.value = selectedFiles
            } else {
                fileNames.value = 'Нет загружаемых файлов'
            }
        }

        const uploadModelFiles = async () => {
            if (modelFiles.value.length === 0) {
                alert('Пожалуйста, добавьте файлы для загрузки.')
                return
            }

            const formData = new FormData()
            for (let i = 0; i < modelFiles.value.length; i++) {
                formData.append('files', modelFiles.value[i])
            }

            try {
                const response = await fetch('/upload_model_files', {
                    method: 'POST',
                    body: formData
                })
                if (response.ok) {
                    closeUploadModal()
                    await loadData()
                    alert('Файлы успешно загружены!')
                    modelFiles.value = []
                    fileNames.value = 'Нет загружаемых файлов'
                    if (fileInput.value) fileInput.value.value = ''
                }
            } catch (error) {
                console.error('Ошибка загрузки:', error)
            }
        }

        const goToGallery = () => {
            emit('navigate', 'index')
        }

        onMounted(() => {
            loadData()
        })

        return {
            datasets,
            photos,
            selectedDataset,
            modelName,
            imgsz,
            epochs,
            batch,
            savePeriod,
            selectedClassDataset,
            className,
            showAnnotatedOnly,
            selectedPhoto,
            filteredPhotos,
            numPhotos,
            datasetName,
            trainSize,
            valSize,
            nonEmptyCount,
            uploadModalOpen,
            fileNames,
            fileInput,
            getFilename,
            filterFiles,
            updateImage,
            trainModel,
            createClass,
            createDataset,
            openUploadModal,
            closeUploadModal,
            updateModelFileLabel,
            uploadModelFiles,
            goToGallery
        }
    }
}

// Основное приложение с роутингом
createApp({
    setup() {
        const currentPage = ref('index')

        const navigate = (page) => {
            currentPage.value = page
        }

        return { currentPage, navigate }
    },
    components: { IndexPage, ModelPage },
    template: `
        <IndexPage v-if="currentPage === 'index'" @navigate="navigate" />
        <ModelPage v-else-if="currentPage === 'model'" @navigate="navigate" />
    `
}).mount('#app')