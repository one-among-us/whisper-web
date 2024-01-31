<script lang="ts">
    import { onMount } from 'svelte';
    import {HOST} from "./config";

    export let id: string;
    let progress = '';
    let isDone = false;

    onMount(() => {
        checkProgress();
    });

    async function checkProgress() {
        const response = await fetch(`${HOST}/progress/${id}`);
        const data = await response.json();

        if (data.done) {
            isDone = true;
            downloadResults();
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
    {#if isDone}
        <p>Transcription complete. Your file will download shortly.</p>
    {:else}
        <p>Progress: {progress}</p>
    {/if}
</main>
