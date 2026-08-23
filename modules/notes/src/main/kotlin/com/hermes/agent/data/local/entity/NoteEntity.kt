package com.hermes.agent.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Entity(tableName = "notes")
data class NoteEntity(
    @PrimaryKey val id: String,
    val title: String,
    val content: String,
    val tagsJson: String,
    val category: String,
    val isStarred: Boolean,
    val folder: String?,
    val createdAt: Long,
    val updatedAt: Long,
) {
    fun toDomain() = com.hermes.agent.domain.model.Note(
        id = id,
        title = title,
        content = content,
        tags = runCatching { Json.decodeFromString<List<String>>(tagsJson) }.getOrDefault(emptyList()),
        category = category,
        isStarred = isStarred,
        folder = folder,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    companion object {
        fun fromDomain(note: com.hermes.agent.domain.model.Note) = NoteEntity(
            id = note.id,
            title = note.title,
            content = note.content,
            tagsJson = Json.encodeToString(note.tags),
            category = note.category,
            isStarred = note.isStarred,
            folder = note.folder,
            createdAt = note.createdAt,
            updatedAt = note.updatedAt,
        )
    }
}