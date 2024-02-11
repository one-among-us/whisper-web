<script lang="ts">
    import { onMount } from 'svelte';
    import {HOST} from "./config";
    import moment from 'moment';

    interface Chunk {
        timestamp: [number, number],
        text: string,
        speaker?: string
    }

    export let id: string;
    let progress = '';
    let isDone = false;
    let result: {
        output: {
            text: string
            chunks: Chunk[]
        },
        elapsed: number[]
        elapsedStr: string
    }

    onMount(() => {
        checkProgress();
    });

    async function checkProgress() {
        const response = await fetch(`${HOST}/progress/${id}`);
        const data = await response.json();

        if (data.done) {
            isDone = true;
            const tmp = (await fetch(`${HOST}/result/${id}.json`).then(res => res.json()));
            if (typeof tmp.elapsed === 'number') {
                tmp.elapsed = [result.elapsed, 0];
            }
            result = tmp;

            for (const chunk of result.output.chunks)
                chunk.speaker = chunk.speaker?.replace("SPEAKER_0", "")

            console.log(result)
            await downloadResults();
        } else {
            progress = data.status;
            setTimeout(checkProgress, 1000); // Check progress regularly
        }
    }

    async function downloadResults() {
        // Write to timestamped text file
        const output = result.output;
        let txt = "";
        let lastSpeaker = "";

        output.chunks.forEach(c => {
            let _start = c.timestamp[0];
            let speaker = c.speaker ?? "?";

            // Convert seconds to 00:00:00 format
            let start = new Date(_start * 1000).toISOString().substring(11, 19);
            if (speaker !== lastSpeaker) {
                txt += `\n[Speaker ${speaker}]\n`;
                lastSpeaker = speaker;
            }
            txt += `${start}: ${c.text}\n`;
        });

        download(txt, `${id}.txt`, 'text/plain');
    }

    function download(content: string, fileName: string, contentType: string) {
        const a = document.createElement('a');
        const file = new Blob([content], { type: contentType });
        a.href = URL.createObjectURL(file);
        a.download = fileName;
        a.click();
    }
</script>

<main>
    <h1>Transcription Progress</h1>
    {#if isDone && result}
        <p>Transcription complete ({result.elapsed[0].toFixed(1)}s + {result.elapsed[1].toFixed(1)}s). Your file will download shortly.</p>
        <a href={`${HOST}/result/${id}.txt`} download>Download</a>
        <div class="chunks">
            {#each result.output.chunks as chunk}
                <div>
                    <span>{moment.utc(chunk.timestamp[0] * 1000).format("HH:mm:ss")}</span>
                    <span class="speaker s{chunk.speaker}">{chunk.speaker ?? "?"}</span>
                    <p>{chunk.text}</p>
                </div>
            {/each}
        </div>
    {:else}
        <p>Progress: {progress}</p>
    {/if}
</main>

<style lang="sass">
    .chunks
      div
        display: flex
        align-items: center
        gap: 1rem

        text-align: left

        > span
          font-family: monospace

        .speaker
          color: #ff9595
        .s0
          color: #59ffa1
        .s1
          color: #597aff
</style>
