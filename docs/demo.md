# GENESIS ArtTech demonstration

Show the audience one detail first. In **Дорога после дождя**, the lamp reflection stays on screen after its caption disappears. Start with that silence in the narration, then show where the words, image and rhythm came from.

## Prepare the recording

Start the demo with FFmpeg available so the soundtrack comparison uses measured cuts. Keep the rain note easy to reach from **Мой стол**. For the capture segment, open a private Telegram chat with the configured bot. If both modes run on the same machine, use a separate port for the demo. A browser-only recording can use **Создать** in the demo and follow the same preview and publication steps. [Launch instructions](../README.md)

Prepare one rain photograph and an original WAV for the live capture. The following command writes the bundled rain score as a file you can upload. [Rain photograph](../demo/photos/rain-1.jpg)

```sh
mkdir -p var
python -c 'from pathlib import Path; from demo.score import make_score; Path("var/demo-tour.wav").write_bytes(make_score("rain"))'
```

## Run of show · 2 minutes 55 seconds

| Time | On screen | Speaker cue |
| --- | --- | --- |
| 0:00–0:20 | Open the seeded rain note from the table. Tap **Пережить день** and allow the final reflection to hold. | «От целого дня мне запомнился фонарь, который дрожал в луже». |
| 0:20–0:52 | In the bot, send «В автобусе какао обжигало ладони. Фонарь дрожал в луже», the photo and the WAV. Choose a character if prompted. Tap **Собрать воспоминание**, then **Сохранить день**. Trim waiting time in the recording. | «Это мои слова, снимок и музыка. Я вижу монтаж до сохранения». |
| 0:52–1:10 | Tap **Открыть день** in the confirmation. Show the original story and photo in the folder and play the track. Return to the table. | «Из сообщения я попадаю прямо в свою запись. Здесь можно перечитать историю, посмотреть исходные снимки и переслушать песню». |
| 1:10–1:50 | Open the fictional park note and tap **Сравнить монтаж** beside **Пережить день**. Select **Тепло в ладонях**, **Ровный монтаж** or **На шаг быстрее**, then use **Пережить день** to play the selected edit. Capture a short excerpt of each. | «Сначала меняется только длительность кадров, музыка та же. Затем меняю дорожку и смотрю, как новый ритм сдвигает склейки». |
| 1:50–2:17 | Show the office's last still on **Отправили** and the letter on the platform against a rhythmic track. Search **какао** in the archive. | «Темп перехода и движение внутри фотографии можно почувствовать отдельно. А найти день можно даже по одному слову». |
| 2:17–2:55 | Select three days in the archive, open **В монтажную**, edit a chapter caption, save and play the Life Replay. Finish with the three chapter dates and the project links. | «Это три записи из моего дневника. У каждой остался свой голос, но теперь я могу посмотреть их вместе». |

## What to compare during rehearsal

A fresh demo runs all six stories through the ordinary generation path. The park, office and platform have different camera travel, shot lengths and final lines. The rain and park folders include alternate soundtracks. **Почему так выглядит день?** surfaces decisions from the scene data. Switch the table between **Бумага** and **Неон** to show that the environment can change without recutting the memory.

Use uploaded or bundled audio for the synchronization comparison. A service link opens via **Открыть песню**. If presenting narration, install the local models and enable the scene voice before recording. Check that the final sound mix has both the soundtrack and the speaker's voice. End on the project link and the confirmed entry point used in the recording. [Submission text](../HACKATHON_SUBMISSION.md) · [Verification record](../IMPLEMENTATION_PROGRESS.md)
