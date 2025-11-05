document.addEventListener('DOMContentLoaded', function () {
  const toggles = document.querySelectorAll('.toggle-password');

  toggles.forEach(toggle => {
    toggle.addEventListener('click', function () {
      const input = document.querySelector(this.getAttribute('toggle'));
      const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
      input.setAttribute('type', type);

      this.classList.toggle('fa-eye');
      this.classList.toggle('fa-eye-slash');
    });
  });
});
