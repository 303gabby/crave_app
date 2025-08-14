
// responsive navbar
const menuBtnEl = document.querySelector('.menu-button');
const navbarEl = document.querySelector('.nvbar');
const closeBtnEl = document.querySelector('.x-mark-button');

menuBtnEl.addEventListener('click', (e) => {
    e.preventDefault()
    navbarEl.classList.toggle('show');
})

closeBtnEl.addEventListener('click', (e) => {
    e.preventDefault()
    navbarEl.classList.remove('show');
})
