
// Toggle Password Visibility
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



// Password Strength Checker 

document.addEventListener("DOMContentLoaded", function () {

    const passwordInput = document.getElementById("password-field");

    // Only run on signup page
    if (!passwordInput) return;

    const ruleLength = document.getElementById("rule-length");
    const ruleUpper = document.getElementById("rule-upper");
    const ruleLower = document.getElementById("rule-lower");
    const ruleNumber = document.getElementById("rule-number");
    const ruleSpecial = document.getElementById("rule-special");

    passwordInput.addEventListener("input", function () {
        const p = passwordInput.value;

        updateRule(ruleLength, p.length >= 12);
        updateRule(ruleUpper, /[A-Z]/.test(p));
        updateRule(ruleLower, /[a-z]/.test(p));
        updateRule(ruleNumber, /[0-9]/.test(p));
        updateRule(ruleSpecial, /[!@#$%^&*(),.?":{}|<>_\-]/.test(p));
    });

    function updateRule(element, condition) {
        if (!element) return;

        if (condition) {
            element.classList.remove("text-danger");
            element.classList.add("text-success");
            element.innerHTML = "✔ " + element.innerHTML.slice(element.innerHTML.indexOf(" ") + 1);
        } else {
            element.classList.remove("text-success");
            element.classList.add("text-danger");
            element.innerHTML = "✖ " + element.innerHTML.slice(element.innerHTML.indexOf(" ") + 1);
        }
    }
});
