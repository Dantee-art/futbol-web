// Función para colapsar/expandir las ligas al hacer clic en su barra superior
function toggleLeague(element) {
    const matchesContainer = element.nextElementSibling;
    const arrow = element.querySelector('.toggle-arrow');
    
    // getComputedStyle lee el estado real del CSS
    const isHidden = window.getComputedStyle(matchesContainer).display === "none";
    
    if (isHidden) {
        matchesContainer.style.display = "block";
        if (arrow) arrow.style.transform = "rotate(0deg)";
    } else {
        matchesContainer.style.display = "none";
        if (arrow) arrow.style.transform = "rotate(180deg)";
    }
}

// Función para simular el cambio de filtros en la barra superior
// NOTA: Se agregó 'event' como segundo parámetro
function filterMarket(marketType, event) {
    const buttons = document.querySelectorAll('.market-btn');
    
    // Le quitamos la clase activa a todos los botones
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Se la agregamos al botón específico que recibió el clic
    if (event) {
        event.currentTarget.classList.add('active'); 
    }
    
    // Aquí puedes programar en el futuro qué partidos mostrar
    console.log("Filtro seleccionado: " + marketType);
}

