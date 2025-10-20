<script>
document.getElementById('trait-form').addEventListener('submit', function(e) {
  e.preventDefault();  // ⛔ Отключить перезагрузку

  const formData = new FormData(this);
  fetch('/add_trait', {
    method: 'POST',
    body: formData
  })
  .then(res => res.ok ? res.text() : Promise.reject(res.status))
  .then(() => {
    document.getElementById('trait-status').classList.remove('hidden');
    this.reset();  // Очистить форму
  })
  .catch(err => {
    alert("Ошибка при добавлении: " + err);
  });
});
</script>