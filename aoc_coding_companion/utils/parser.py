import re
from pathlib import Path
from typing import List, Dict, Optional

import aiohttp
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from pydantic import BaseModel
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_exponential


class ParserConfig(BaseModel):
    headers: dict
    cookies: dict

    def __str__(self) -> str:
        return f"Config(headers={self.headers}, cookies=HIDDEN_FOR_SECURITY)"


class Leader(BaseModel):
    position: Optional[int]
    name: str
    points: int

    def __str__(self) -> str:
        return f"Участник №{self.position} (имя={self.name}, очки={self.points})"


class LeaderboardResult(BaseModel):
    leaders: List[Leader]
    my_position: Optional[int] = None
    my_points: Optional[int] = None

    def __str__(self) -> str:
        return (
            f"Таблица результатов(\n"
            f"  5 первых участников: {' | '.join(map(str, self.leaders[:5]))}\n"
            f"  Твоя позиция: {self.my_position}\n"
            f"  Твои очки: {self.my_points}\n)"
        )


class PuzzleStatus(BaseModel):
    fully_solved: Dict[str, str]
    partially_solved: Dict[str, str]
    unsolved: Dict[str, str]

    def __str__(self) -> str:
        return (
            f"Статусы задач(\n"
            f"  Полностью решены: {len(self.fully_solved)} задач\n"
            f"  Частично решены: {len(self.partially_solved)} задач\n"
            f"  Не решены: {len(self.unsolved)} задач\n)"
        )


class CalendarResults(BaseModel):
    released: PuzzleStatus
    not_released: List[str]

    def __str__(self) -> str:
        released = str(self.released).replace('\n', '\n\t')
        return (
            f"Анализ календаря(\n"
            f"  Выпущенные задачи:\n\t{released}\n"
            f"  Не выпущенные задачи: {len(self.not_released)} задач\n)"
        )


class PuzzleDetail(BaseModel):
    name: str
    description: str
    question: str
    day_url: str
    level: int

    @property
    def input_link(self) -> str:
        return urljoin(self.day_url if self.day_url.endswith('/') else f"{self.day_url}/", 'input')

    @property
    def submit_url(self) -> str:
        return urljoin(self.day_url if self.day_url.endswith('/') else f"{self.day_url}/", 'answer')

    def __str__(self) -> str:
        return (
            f"Детали задачи:(\n"
            f"  Ссылка: {self.day_url}\n"
            f"  Название: {self.name}\n"
            f"  Описание: {repr(self.description[:100])}...\n"
            f"  Основной вопрос: {self.question}\n"
            f"  Часть задачи: {self.level}\n"
        )


class SubmissionResult(BaseModel):
    is_correct: bool = False
    full_text: str

    def __str__(self) -> str:
        return (
            f"Результат проверки(\n"
            f"  Правильность: {self.is_correct}\n"
            f"  Полный текст ответа: {self.full_text}\n)"
        )


class AdventOfCodeParser:
    BASE_URL = "https://adventofcode.com"
    WAIT_BUFFER = 30

    def __init__(self, config: ParserConfig, year: Optional[int] = None):
        self.config = config
        self.year = year if year is not None else datetime.now().year
        self.session = None  # Сессия создается в контекстном менеджере

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.config.headers, cookies=self.config.cookies)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_page(self, url: str) -> str:
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    @staticmethod
    def _extract_puzzle_details(soup: BeautifulSoup, day_url: str) -> PuzzleDetail:
        day_descriptions = soup.find_all('article', class_='day-desc')
        if not day_descriptions:
            raise ValueError("Проблема с нахождением описания задачи.")

        full_description = []
        name = ""
        question = ""

        for desc in day_descriptions:
            title_tag = desc.find('h2')
            if title_tag and not name:
                name = title_tag.get_text(strip=True)

            section_parts = []
            for el in desc.children:
                section_parts.append(el.get_text(separator=' ', strip=True))
            section_text = "\n".join(section_parts)

            full_description.append(section_text)

            em_tags = desc.find_all('em')
            if em_tags:
                question = em_tags[-1].get_text(strip=True)

        description = "\n\n\n".join(full_description)

        level = 1

        success_tag = soup.find('p', class_='day-success')
        if success_tag:
            success_text = success_tag.get_text(strip=True)
            level += success_text.startswith("The first half of this puzzle is complete!")
            level += success_text.startswith("Both parts of this puzzle are complete!")

        return PuzzleDetail(
            name=name,
            description=description,
            question=question,
            day_url=day_url,
            level=level
        )

    @staticmethod
    def _extract_leaderboard(soup: BeautifulSoup) -> LeaderboardResult:
        user_div = soup.find('div', class_='user')
        my_name = "".join(user_div.find_all(string=True, recursive=False)).strip() if user_div else None

        leaders = []
        leader_rows = soup.find_all('div', class_='privboard-row')

        my_position = None
        my_points = None

        for row in leader_rows:
            try:
                name_tag = row.find('span', class_='privboard-name')
                if not name_tag:
                    continue

                name = name_tag.text.strip()

                position = None
                position_tag = row.find('span', class_='privboard-position')
                if position_tag:
                    position_str = position_tag.text.strip().replace(')', '')
                    try:
                        position = int(position_str)
                    except ValueError:
                        print(f"Не удалось преобразовать позицию в числовое значение: '{position_str}'")

                points_str = None
                for text in row.stripped_strings:
                    if text.isdigit():
                        points_str = text
                        break

                if points_str is None:
                    raise ValueError("Очки не найдены.")

                points = int(points_str)

                leaders.append(Leader(position=position, name=name, points=points))

                if my_name and name.lower() == my_name.lower():
                    my_position = position
                    my_points = points

            except Exception as e:
                print(f"Ошибка при обработке участника: {e}")
                continue

        return LeaderboardResult(leaders=leaders, my_position=my_position, my_points=my_points)

    def _extract_calendar(self, soup: BeautifulSoup) -> CalendarResults:
        calendar = soup.find('pre', class_='calendar')

        solved_complete = {}
        solved_partial = {}
        unsolved = {}
        not_released = []

        for day_tag in calendar.find_all(['a', 'span']):
            day_number_tag = day_tag.find('span', class_='calendar-day')
            if day_number_tag is not None:
                day_number = day_number_tag.text.strip()
                if day_tag.name == 'a':
                    href = day_tag.get('href', '')
                    link = urljoin(self.BASE_URL, href)
                    if 'calendar-verycomplete' in day_tag['class']:
                        solved_complete[day_number] = link
                    elif 'calendar-complete' in day_tag['class']:
                        solved_partial[day_number] = link
                    else:
                        unsolved[day_number] = link
                else:
                    not_released.append(day_number)

        return CalendarResults(
            released=PuzzleStatus(
                fully_solved=solved_complete,
                partially_solved=solved_partial,
                unsolved=unsolved,
            ),
            not_released=not_released
        )

    async def parse_puzzle_details(self, day_url: str) -> PuzzleDetail:
        html = await self.get_page(day_url)
        soup = BeautifulSoup(html, 'html.parser')
        return self._extract_puzzle_details(soup, day_url)

    async def parse_leaderboard(self, leaderboard_id: int) -> LeaderboardResult:
        board_url = f"{self.BASE_URL}/{self.year}/leaderboard/private/view/{leaderboard_id}"
        html = await self.get_page(board_url)
        soup = BeautifulSoup(html, 'html.parser')

        join_form = soup.find('form', action=f"/{self.year}/leaderboard/private/join")
        if join_form:
            raise RuntimeError("Лидерборд недоступен или вы не являетесь его участником.")

        return self._extract_leaderboard(soup)

    async def parse_calendar(self) -> CalendarResults:
        url = f"{self.BASE_URL}/{self.year}/"
        html = await self.get_page(url)
        soup = BeautifulSoup(html, 'html.parser')
        return self._extract_calendar(soup)

    async def submit_answer(self, submit_url: str, level: int, answer: str) -> SubmissionResult:
        form_data = {
            'level': level,
            'answer': answer
        }

        async with self.session.post(submit_url, data=form_data) as response:
            response.raise_for_status()
            text = await response.text()

        soup = BeautifulSoup(text, 'html.parser')
        article = soup.find('article')
        full_text = article.get_text(strip=True) if article else "Ответ не получен."

        if full_text.startswith('You gave an answer too recently'):
            match = re.search(r'(\d+)m (\d+)s', full_text)

            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                total_seconds = minutes * 60 + seconds
                wait_seconds = total_seconds + self.WAIT_BUFFER
                print(f'Необходимо подождать {wait_seconds} секунд для отправки ответа.')

                await asyncio.sleep(wait_seconds)
                return await self.submit_answer(submit_url, level, answer)
        elif full_text.endswith('please wait 10 minutes before trying again.[Return to Day 1]'):
            wait_seconds = 10 * 60 + self.WAIT_BUFFER
            print(f'Необходимо подождать {wait_seconds} секунд для отправки ответа.')
            await asyncio.sleep(wait_seconds)
            return await self.submit_answer(submit_url, level, answer)

        is_correct = full_text.startswith("That's the right answer!")

        return SubmissionResult(is_correct=is_correct, full_text=full_text)

    async def download_input(self, input_url: str, save_path: Path) -> None:
        async with self.session.get(input_url) as response:
            response.raise_for_status()
            content = await response.content.read()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        content = content.rstrip(b'\n')

        with save_path.open('wb') as file:
            file.write(content)
        print(f"Данные успешно сохранены в {save_path}")


async def main():
    config = ParserConfig(
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) Gecko/20100101 Firefox/92.0',
        },
        cookies={
            'session': '53616c7465645f5f80026031ebcf06062a0caa867512aa340b1c5acd7b5439b25d480e5a447a3a28d03b7e4b8c66862d5923a496055d7ef5e0fceeeae9ed4e31',
        }
    )

    async with AdventOfCodeParser(config) as parser:
        try:
            calendar_results = await parser.parse_calendar()
            print(calendar_results)
            print(calendar_results.released.partially_solved)

            # if calendar_results.released.partially_solved:
            #     day_url = calendar_results.released.partially_solved['6']
            #     puzzle_details = await parser.parse_puzzle_details(day_url)
            #     print(puzzle_details)
            #
            #     if puzzle_details:
            #         submission_result = await parser.submit_answer(puzzle_details.submit_url, level=2, answer='0')
            #         print(submission_result)

        except RuntimeError as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
