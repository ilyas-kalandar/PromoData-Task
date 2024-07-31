### 🕷 Bethowen crawler
Тестовое задание от PromoData

Экзампл выхлопа парсера расположен в /ext/ (в корне репоза)

**ВАЖНО**: Я не осилил многое, например фильтры, но загрузку сделал, у меня через таджикский IP вовсе не отдаются данные, я грузил через российский VPN

Так вот, после загрузки N-го количества данных, краулер падает (IP блокируется), конечно я реализовал КЕШ, чтобы можно было продолжить если что, ну и реализовал возможность использования прокси, я больше не вижу вариантов решения, т.к не занимаюсь подобоными вещами.

### Как установить
Я обожаю poetry, рекомендую и вам его себе поставить

##### MacOS/Linux 

```bash
curl -sSL https://install.python-poetry.org | python3 -
```
##### Винда

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

#### Грузим репозиторий

```bash
git clone https://github.com/ilyas-kaladar/PromoData-Task
cd PromoData-Task
```

#### Установка зависимостей


```bash
poetry install
```

Откроем poetry-shell

```bash
poetry shell
```

#### Создадим `settings.yaml` для конфигурации

Только на юниксах
```bash
touch settings.yaml
```
Можете воспользоваться готовым конфигом, пусть будет как экзампл,
думаю все понятно, очевидно, что должен быть установлен Redis

```yaml
output_file: out.csv
base_url: https://bethowen.ru/
requests_to_delay: 10
delay: 10
threads: 8
redis:
  host: localhost
  port: 6379
```

#### 🚀 Запустим проект
```
python -m crawler clean # Для очистки кеша и.т.д
python -m cralwer run # Для запуска процесса краулинга
```

