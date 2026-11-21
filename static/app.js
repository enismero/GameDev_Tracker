//api ile haberleşme
console.log("app.js çalışıyor");

const statuses={
    todo: "yapılacak",
    in_progress:"devam ediyor",
    testing:"test ediliyor",
    done:"tamamlandı"
};

const priorities = {
    low: "Düşük",
    medium: "Orta",
    high: "Yüksek"
};
//CSS seçicisine uyan ilk HTML elemanını bulur.
const board = document.querySelector("#board");
const form = document.querySelector("#task-form");
const message = document.querySelector("#message");
const submitButton = document.querySelector("#submit-button");
const refreshButton = document.querySelector("#refresh-button");

function showMessage(text, isError = false) {
    message.textContent = text;
    message.classList.toggle("error", isError);
}

// API'ye istek gönder ve hata varsa yakalanabilecek bir hata üret.
async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);//HTTP isteği gönderir,
    const data = await response.json(); //JSON yanıtını JavaScript verisine dönüştürür.

    if (!response.ok) {
        let detail = data.detail;

        if (Array.isArray(detail)) {
            detail = detail.map(item => item.msg).join(" | ");
        }

        throw new Error(detail || `İstek başarısız: ${response.status}`);
    }

    return data;
}

// Kullanıcı metinlerini HTML olarak yorumlamadan ekle.
function addText(parent, tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;
    element.className = className;
    parent.appendChild(element);
    return element;
}

function createCard(task) {
    const card = document.createElement("article");
    card.className = "card";

    addText(card, "h3", `#${task.task_id} ${task.title}`);

    if (task.description) {
        addText(card, "p", task.description, "description");
    }

    addText(
        card,
        "p",
        `Öncelik: ${priorities[task.priority]} · ` +
        `Sorumlu: ${task.assigned_person || "Atanmamış"}`,
        "meta"
    );

    const select = document.createElement("select");
    select.setAttribute("aria-label", `${task.title} görev durumu`);

    for (const [value, label] of Object.entries(statuses)) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }

    select.value = task.status;

    select.addEventListener("change", async () => {
        const previousStatus = task.status;
        select.disabled = true;

        try {
            await apiRequest(`/tasks/${task.task_id}/status`, {
                method: "PATCH",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({status: select.value})
            });

            showMessage("Görev durumu güncellendi.");
            await loadTasks();
        } catch (error) {
            select.value = previousStatus;
            showMessage(error.message, true);
        } finally {
            select.disabled = false;
        }
    });

    card.appendChild(select);
    return card;
}

async function loadUsers() {
    const creatorSelect = document.querySelector("#created-by");
    const assigneeSelect = document.querySelector("#assigned-to");

    submitButton.disabled = true;

    try {
        const users = await apiRequest("/users");

        // İlk açıklama seçeneklerini koru, eski kullanıcıları kaldır.
        creatorSelect.length = 1;
        assigneeSelect.length = 1;

        for (const user of users) {
            const label = `${user.display_name} (#${user.user_id})`;

            const creatorOption = document.createElement("option");
            creatorOption.value = user.user_id;
            creatorOption.textContent = label;
            creatorSelect.appendChild(creatorOption);

            const assigneeOption = document.createElement("option");
            assigneeOption.value = user.user_id;
            assigneeOption.textContent = label;
            assigneeSelect.appendChild(assigneeOption);
        }

        if (users.length === 0) {
            showMessage(
                "Henüz kullanıcı yok. Görev eklemek için önce kullanıcı oluşturmalısın.",
                true
            );
            return;
        }

        submitButton.disabled = false;

    } catch (error) {
        showMessage(`Kullanıcılar yüklenemedi: ${error.message}`, true);
    }
}

async function loadTasks() {
    refreshButton.disabled = true;

    try {
        const tasks = await apiRequest("/tasks");
        board.replaceChildren();

        for (const [status, label] of Object.entries(statuses)) {
            const column = document.createElement("section");
            column.className = "column";

            const matchingTasks = tasks.filter(task => task.status === status);
            addText(column, "h2", `${label} (${matchingTasks.length})`);

            if (matchingTasks.length === 0) {
                addText(column, "p", "Henüz görev yok.", "empty");
            }

            for (const task of matchingTasks) {
                column.appendChild(createCard(task));
            }

            board.appendChild(column);
        }
    } catch (error) {
        showMessage(`Pano yüklenemedi: ${error.message}`, true);
    } finally {
        refreshButton.disabled = false;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const title = document.querySelector("#title").value.trim();
    const assignedTo = document.querySelector("#assigned-to").value;

    if (!title) {
        showMessage("Görev başlığı boş olamaz.", true);
        return;
    }

    const task = {
        title: title,
        description: document.querySelector("#description").value.trim() || null,
        priority: document.querySelector("#priority").value,
        created_by: Number(document.querySelector("#created-by").value),
        assigned_to: assignedTo ? Number(assignedTo) : null
    };

    submitButton.disabled = true;

    try {
        await apiRequest("/tasks", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(task)
        });

        document.querySelector("#title").value = "";
        document.querySelector("#description").value = "";

        showMessage("Görev oluşturuldu.");
        await loadTasks();
    } catch (error) {
        showMessage(error.message, true);
    } finally {
        submitButton.disabled = false;
    }
});

refreshButton.addEventListener("click", () => {
    showMessage("");
    loadTasks();
});
loadUsers()
loadTasks();