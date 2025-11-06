const modal = document.getElementById('modal');
const modalBody = document.getElementById('modal-body');

document.querySelectorAll('.modal-link').forEach(link => {
    link.addEventListener('click', async (e) => {
        e.preventDefault();
        document.body.style.overflow = 'hidden';

        try {
            const url = link.dataset.url;
            const res = await fetch(url, { method: 'GET', headers: { 'X-Requested-With': 'fetch' }, cache: 'no-store' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const html = await res.text();
            modalBody.innerHTML = html;
        } catch (err) {
            modalBody.innerHTML = '<div class="error">Не удалось загрузить содержимое. Повторите попытку позже.</div>';
            console.error(err);
        }
        modal.classList.remove('hidden');
        modalBody.parentElement.scrollTop = 0;
    });
});


function closeModal() {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeModal();
});