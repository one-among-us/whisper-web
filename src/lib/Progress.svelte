<script lang="ts">
    import { onMount } from 'svelte';
    import {HOST} from "./config";
    import moment from 'moment';

    interface Chunk {
        timestamp: [number, number],
        text: string
    }

    export let id: string;
    let progress = '';
    let isDone = false;
    let result: {
        output: {
            text: string
            chunks: Chunk[]
        },
        elapsed: number
    }

    onMount(() => {
        checkProgress();
    });

    async function checkProgress() {
        const response = await fetch(`${HOST}/progress/${id}`);
        const data = await response.json();

        if (data.done) {
            isDone = true;
            result = (await fetch(`${HOST}/result/${id}.json`).then(res => res.json()));
            console.log(result)
            await downloadResults();
        } else {
            progress = data.status;
            setTimeout(checkProgress, 1000); // Check progress regularly
        }
    }

    async function downloadResults() {
        const response = await fetch(`${HOST}/result/${id}.txt`);
        const text = await response.text();
        download(text, `${id}.txt`, 'text/plain');
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
        <p>Transcription complete ({result.elapsed.toFixed(1)}s). Your file will download shortly.</p>
        <a href={`${HOST}/result/${id}.txt`} download>Download</a>
        <div class="chunks">
            {#each result.output.chunks as chunk}
                <div>
                    <span>{moment.utc(chunk.timestamp[0] * 1000).format("HH:mm:ss")}</span>
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
</style>
