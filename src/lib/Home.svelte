<script lang="ts">
    import { HOST } from './config'
    import Icon from '@iconify/svelte'

    let isDragging = false
    let isUploading = false
    let error = ""

    function onDragOver(event: DragEvent) {
        event.preventDefault()
        isDragging = true
        error = ""
    }

    function onDragLeave(event: DragEvent) {
        event.preventDefault()
        isDragging = false
    }

    function onDrop(e: DragEvent) {
        e.preventDefault()
        isDragging = false

        let _files = e.dataTransfer?.files
        if (!_files) return
        let files = Array.from(_files)

        // One file at a time
        if (files.length > 1)
            return error = 'Please upload one file at a time'

        let file = files[0]

        console.log('Uploading', file.name, file.size, file.type)
        upload(file)
    }

    async function upload(file: File) {
        isUploading = true
        error = ""

        // Upload file
        let formData = new FormData()
        formData.append('file', file)

        const res = await fetch(`${HOST}/upload`, {
            method: 'POST',
            body: formData
        }).then(res => res.json())

        console.log('Upload result', res)

        // Result should be a UUID
        if (res.error) {
            error = res.error
        } else {
            // Redirect to /:uuid
            window.location.href = `/${res.audio_id}`;
        }
    }

    function onFileChange(e: Event) {
        let input = e.target as HTMLInputElement
        let file = input.files?.[0]
        if (!file) return
        upload(file)
    }
</script>

<div>
    <div class="drop-area" on:dragover={onDragOver} on:dragleave={onDragLeave} on:drop={onDrop}>
        {#if isUploading}
            Uploading...
        {:else if error}
            {error}
        {:else}
            Drop file to upload
        {/if}
    </div>

    <div class="upload-btn">
        <input type="file" id="file" on:change={onFileChange} />
        <label for="file"><Icon icon="tabler:upload"/></label>
    </div>
</div>

<style lang="sass">
  body
    font-family: 'Arial', sans-serif

  $c-emp: #86a2ff
  $c-error: #ff8e8e

  .drop-area
    z-index: 100

    border: 2px dashed $c-emp
    border-radius: 1rem
    background: rgba(white, 0.2)

    // Blur
    backdrop-filter: blur(10px)

    position: fixed
    inset: 0
    margin: 5rem

    display: flex
    flex-direction: column
    align-items: center
    justify-content: center
    text-align: center

    font-size: 3em
    color: $c-emp

  .drop-area.error
    border-color: $c-error
    color: $c-error

  .upload-btn
    position: fixed
    bottom: 3rem
    right: 3rem

    z-index: 110

    background: $c-emp
    width: 50px
    height: 50px
    border-radius: 50%

    color: white
    display: flex
    align-items: center
    justify-content: center

    box-shadow: 0 3px 5px rgba(black, 0.4)

    cursor: pointer

    input
      display: none
</style>
