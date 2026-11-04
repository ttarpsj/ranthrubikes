import './bootstrap';
import './rank';
import './drawer-tabs';

const thumbnail = document.createElement('link');
thumbnail.rel = 'icon';
thumbnail.type = 'image/png';
thumbnail.href = `${import.meta.env.BASE_URL}images/ran-thru.png`;
document.head.appendChild(thumbnail);

document.querySelectorAll('.logo, .drawer-logo').forEach((wordmark) => {
    const image = document.createElement('img');
    image.src = `${import.meta.env.BASE_URL}images/ran-thru.svg`;
    image.alt = 'Ran Thru Bikes';
    wordmark.replaceChildren(image);
});

document.querySelectorAll('[data-back-to-top]').forEach((control) => control.addEventListener('click', (event) => {
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}));

document.querySelectorAll('[data-ride-calculator]').forEach((calculator) => {
    const update = () => {
        const distance = Number(calculator.querySelector('[data-route]').value);
        const [hour, minute] = calculator.querySelector('[data-start]').value.split(':').map(Number);
        const minutes = Math.round((distance / Number(calculator.querySelector('[data-speed]').value || 21)) * 60)
            + Number(calculator.querySelector('[data-breakfast]').value || 0)
            + Number(calculator.querySelector('[data-stops]').value || 0)
            + Number(calculator.querySelector('[data-detours]').value || 0) * 10;
        const finish = new Date(2026, 10, 7, hour, minute + minutes);
        calculator.querySelector('[data-finish]').textContent = `ESTIMATED FINISH — ${finish.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    };
    calculator.querySelectorAll('input, select').forEach((input) => input.addEventListener('input', update));
    update();
});
