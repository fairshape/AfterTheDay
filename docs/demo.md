# Three-minute demo

## Before presenting

Follow the [launch instructions](../README.md). Keep the fictional archive open in a browser. For a live creation, run another instance with `BOT_TOKEN`, `WEBAPP_URL`, and `DEMO_MODE=false`, and open the bot in a Telegram private chat. Use two ports if both instances run on the same machine.

Use a real team day if you have one and can share it. No team material accompanied this prototype. For the fictional live walkthrough, have [rain-1.jpg](../demo/photos/rain-1.jpg) ready to send and prepare the original audio file after starting the demo once.

```sh
python -c 'from pathlib import Path; from demo.score import make_score; Path("var/demo-tour.wav").write_bytes(make_score("calm"))'
```

## Run of show

| Time | On screen and narration |
| --- | --- |
| 0:00–0:15 | Show the Telegram chat and say, “After the Day is a private film journal. The part I want to remember might be as small as a streetlight in a puddle.” |
| 0:15–0:52 | Tap **Записать день**. Send “Дорога после дождя. В автобусе какао обжигало ладони. Фонарь дрожал в луже.” Send the photo and WAV. Choose **Мягкий** if prompted. Tap **Собрать воспоминание**, preview the scene, then tap **Сохранить день**. |
| 0:52–1:20 | Tap **Пережить день** and let the photo move while the piano plays. Close the player and scroll to the story, gallery, and song. Tap **В дневник** and reopen the same entry. |
| 1:20–2:03 | Switch to the fictional archive and open **Осенний парк и какао**. Compare **Тепло в ладонях** with **Ровный монтаж** on the same excerpt, then switch to **На шаг быстрее**. Call attention to the shorter holds, sharper cuts, and quicker push-in on exactly the same photos. Open **Почему так выглядит день?** to show the saved values. |
| 2:03–2:30 | Open **Смех на кухне** and show the warm, rhythmic kitchen cuts. Preview a voice sample under **Голос** or toggle the scene microphone to hear the soundtrack duck. |
| 2:30–2:55 | Open **Ночь в офисе перед сдачей** and let it run through to the still **Отправили** frame. Return to the archive and type **какао** to show how a remembered word brings back the rainy day. |

If Telegram is unavailable at the venue, open the six-day local demo archive and use the park, office, and kitchen folders and use the first part of the presentation to show the story, gallery, and song below the cover. The local archive demonstrates generation and replay.
