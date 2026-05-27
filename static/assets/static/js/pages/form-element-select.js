let choices = document.querySelectorAll(".choices");

choices.forEach(el => {
  let config = {};
  if (el.classList.contains("multiple-remove")) {
    config = {
      delimiter: ",",
      editItems: true,
      maxItemCount: -1,
      removeItemButton: true,
    };
  }

  el.choices = new Choices(el, config);
});