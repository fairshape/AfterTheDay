# A 2 minute 55 second demonstration

Show the audience one detail first. In **Дорога после дождя**, the lamp reflection stays on screen after its caption disappears. Start with that silence in the narration, then show where the words, image and rhythm came from.

## Prepare the two libraries

Start the [local demo](../README.md) with the six fictional days. Keep **Мой стол** open. For the bot segment use a configured private Telegram chat and a public HTTPS endpoint. Use a separate port for the demo if both run on the same machine. With only a browser, use **Создать** in the demo for the recording segment. The browser and Telegram capture routes both write through the same diary service.

Have [the rain photograph](../demo/photos/rain-1.jpg) ready. To create an original audio file for the capture, run this in the active project environment after the first demo startup:

```sh
python -c 'from pathlib import Path; from demo.score import make_score; Path("var/demo-tour.wav").write_bytes(make_score("rain"))'
```

## Run of show

| Time | On screen | Speaker cue |
| --- | --- | --- |
| 0:00–0:20 | Open the seeded rain note from the table. Tap **Пережить день** and allow the final reflection to hold. | After the image settles: «От целого дня мне запомнился фонарь, который дрожал в луже». |
| 0:20–0:52 | In the bot, send «В автобусе какао обжигало ладони. Фонарь дрожал в луже», the photo and the WAV. Choose a character if prompted. Open the proposed memory, then **Сохранить день**. Trim waiting time in the recording. | «Это мои слова, снимок и музыка. Я вижу монтаж до сохранения». |
| 0:52–1:10 | Open the exact day from its confirmation. Show the original story and photo beneath the note and play its track. Return to the table. | Explain how the same day ID connects the bot, note and player. |
| 1:10–1:50 | Switch to the fictional park note. Play a passage from the original score, compare **Ровный монтаж**, then choose **На шаг быстрее**. Keep the photographs and words visible across the cuts. | «Меняем одну вещь — музыку. Сравните, сколько времени остаётся на кадр и на слова “Долго разговаривали”». |
| 1:50–2:17 | Show the office's last still on **Отправили** and the letter on the platform against a rhythmic track. Search **какао** in the archive. | «Темп перехода и движение внутри фотографии можно почувствовать отдельно. А найти день можно даже по одному слову». |
| 2:17–2:55 | Select three days in the archive, open **В монтажную**, edit a chapter caption, save and play the Life Replay. Finish with the three chapter dates and the project links. | «Это три записи из моего дневника. У каждой остался свой голос, но теперь я могу посмотреть их вместе». |

## What to compare during rehearsal

A fresh demo runs all six stories through the ordinary generation path. The park, office and platform have different camera travel, shot lengths and final lines. The rain and park folders include alternate soundtracks. **Почему так выглядит день?** surfaces decisions from the scene data. Switch the table between **Бумага** and **Неон** to show that the environment can change without recutting the memory.

Use uploaded or bundled audio for the synchronization comparison. A service link opens via **Открыть песню**. If presenting narration, install the local models and enable the scene voice before recording. The [submission](../HACKATHON_SUBMISSION.md) contains the Russian project description and the [verification record](../IMPLEMENTATION_PROGRESS.md) lists device checks.
